"""The Construction Sites deliver the purchase, and never many times it.

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
- Now, as the Free Market Construction mod does it: once a site has a laborer, its state takes a modifier that
  cuts the group's jobs by 90%, to the one laborer a level a site hires in its first week, so the site is fully
  staffed. The crew pass marks such a site's state, and the purchase is divided over the marked ("crewed")
  sites only. A site is marked only at 105% staffed or less: one cut while it held more laborers than the cut
  leaves jobs for waits, at no throughput, until a weekly pass finds the surplus gone.

This file runs the script itself. A small interpreter executes the crew pass, the sizing and the self-checks
(common/scripted_effects/te_construction_market_update_effects.txt) and the values
(common/script_values/te_construction_market_sector_placement_values.txt) over a model of the sites, week after
week, under each thing the engine might do with a site's surplus laborers and each order the weekly hiring and
the weekly pulse can come in. It knows only the effects and triggers these scripts use and fails on any other,
so a change to the script either runs here or says what the model lacks.

Run: python3 -m unittest test_construction_market_site_sizing -v
"""
import itertools
import math
import re
import unittest
from pathlib import Path

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
CAPACITY = "te_construction_market_capacity_modifier"
CREW_MARK = "te_cm_site_crew"
CREW_MODIFIER = "te_construction_market_crew_modifier"
EMPLOYEE_MULT = "building_group_te_construction_market_bg_employee_mult"
PURCHASE = "te_construction_market_total_use_target"
# The base game's DEFAULT_MAX_HIRING_RATE: the share of its jobs a building may hire in a week. Measured on
# these sites, 2026-11-13: 119 of 168 sites under ten weeks old held exactly one laborer for each week.
HIRING_RATE = 0.1
# The script's values keep five decimals, so a share times its sites can be a hundred-thousandth over.
ROUNDING = 1e-3

TOKEN = re.compile(r'"[^"]*"|[{}]|\?=|<=|>=|!=|[=<>]|[^\s{}=<>?!"]+')
OPS = ("=", "?=", "<", ">", "<=", ">=", "!=")


def code(path):
    """A script file's text without its comments."""
    return "\n".join(line.split("#", 1)[0] for line in path.read_text(encoding="utf-8-sig").splitlines())


def parse(tokens, pos=0):
    """Items of a block as (key, op, value) in file order; value is a str or a list of items."""
    items = []
    while pos < len(tokens) and tokens[pos] != "}":
        key = tokens[pos]
        if pos + 1 >= len(tokens) or tokens[pos + 1] not in OPS:
            raise ValueError("bare token %r" % key)
        op = tokens[pos + 1]
        if tokens[pos + 2] == "{":
            value, pos = parse(tokens, pos + 3)
            pos += 1  # the closing brace
        else:
            value, pos = tokens[pos + 2], pos + 3
        items.append((key, op, value))
    return items, pos


def load(*paths):
    """{name: body} of every top-level block of the files."""
    out = {}
    for path in paths:
        items, _ = parse(TOKEN.findall(code(path)))
        out.update({key: value for key, _op, value in items if isinstance(value, list)})
    return out


def body_of(text, name):
    """The text of the top-level block `name = { ... }`, to its closing brace in column 0."""
    start = text.index("\n%s = {" % name) + 1
    return text[start:text.index("\n}", start)]


def flat(text):
    return " ".join(text.split())


def compare(left, op, right):
    return {"=": left == right, "?=": left == right, "!=": left != right, ">=": left >= right,
            "<=": left <= right, ">": left > right, "<": left < right}[op]


class Scoped:
    """Something that holds variables, some of which run out."""

    def __init__(self, world):
        self.world = world
        self.vars = {}  # name -> (value, the day it runs out or None)

    def has(self, name):
        if name not in self.vars:
            return False
        if self.vars[name][1] is not None and self.world.day >= self.vars[name][1]:
            del self.vars[name]
            return False
        return True

    def get(self, name):
        if not self.has(name):
            raise AssertionError("var:%s read while unset" % name)
        return self.vars[name][0]


class State(Scoped):
    def __init__(self, world):
        super().__init__(world)
        self.modifiers = []  # names, one entry for each copy


class Site:
    def __init__(self, country, level=1, laborers=0):
        self.country = country
        self.state = State(country.world)
        self.level = level
        self.laborers = laborers
        self.capacity = None  # the capacity modifier's multiplier, or the variable it re-reads

    @property
    def jobs(self):
        cut = 1.0 if self.country.world.inert_cut else 1 + sum(
            self.country.world.cut for name in self.state.modifiers if name == CREW_MODIFIER)
        return round(10 * self.level * cut, 6)

    @property
    def occupancy(self):
        if self.jobs <= 0:
            return math.inf if self.laborers else 0.0
        return self.laborers / self.jobs

    @property
    def crewed(self):
        return self.state.has(CREW_MARK)

    def throughput(self):
        """The engine's 1 plus the capacity modifier, whose multiplier it reads again on later ticks."""
        if self.capacity is None:
            return 1.0
        if isinstance(self.capacity, str):
            return 1.0 + self.country.get(self.capacity)
        return 1.0 + self.capacity

    def delivers(self):
        # One point a level at full staff, times the throughput, times the staffing. Nothing here stops the
        # staffing at 100%: a site with more laborers than jobs is taken to deliver in proportion, which is
        # the case the script must never size.
        return max(0.0, self.throughput()) * self.occupancy * self.level


class Country(Scoped):
    def __init__(self, world, purchase=50.0, ai=True):
        super().__init__(world)
        self.purchase = purchase
        self.ai = ai
        self.sites = []
        world.countries.append(self)

    def site(self, **kwargs):
        self.sites.append(Site(self, **kwargs))
        return self.sites[-1]

    def delivered(self):
        return sum(site.delivers() for site in self.sites)


class World:
    """The sites of some countries, the two script files, and the engine's part: hiring and letting go.

    surplus: what the engine does with laborers above a site's jobs. "at_once" lets them go the moment the
    jobs are cut, "weekly" at the weekly employment update, "never" not at all.
    inert_cut: the state's modifier does not change the jobs (the unverified engine fact).
    labor: laborers a site can find in a week."""

    def __init__(self, surplus="weekly", inert_cut=False, labor=1000):
        self.effects = load(EFFECTS, PLACEMENT)
        self.values = load(VALUES)
        self.cut = float(re.search(r"%s\s*=\s*(-[\d.]+)" % EMPLOYEE_MULT,
                                   body_of(code(MODIFIERS), CREW_MODIFIER)).group(1))
        self.surplus, self.inert_cut, self.labor = surplus, inert_cut, labor
        self.day = 0
        self.globals = {}
        self.countries = []
        self.log = []
        self.errors = []

    # ------------------------------------------------------------ the engine
    def shed(self):
        for country in self.countries:
            for site in country.sites:
                if site.laborers > site.jobs:
                    site.laborers = max(0, math.floor(site.jobs + 1e-9))

    def employment(self):
        """The weekly employment update: surplus laborers go, and a site hires up to a tenth of its jobs."""
        if self.surplus == "weekly":
            self.shed()
        for country in self.countries:
            for site in country.sites:
                room = math.floor(site.jobs + 1e-9) - site.laborers
                may = math.floor(HIRING_RATE * site.jobs + 1e-9)
                site.laborers += max(0, min(room, may, self.labor))

    def run(self, name, scope):
        Run(self).effect(self.effects[name], scope)
        if self.surplus == "at_once":
            self.shed()

    def pulse(self, country):
        self.run("te_construction_market_country_update_data", ("country", country))

    def button(self, country):
        self.run("te_construction_market_apply_per_site_modifier", ("country", country))

    def week(self, hiring_first=True, days=7):
        """Seven days with one employment update and one pulse for every country, in either order."""
        self.day += days
        if hiring_first:
            self.employment()
        for country in self.countries:
            self.pulse(country)
        if not hiring_first:
            self.employment()

    def lines(self, name):
        return [line for line in self.log if " %s " % name in line]


class Run:
    """One execution of an effect."""

    def __init__(self, world):
        self.world = world

    # ------------------------------------------------------------ values
    def value(self, token, scope):
        kind, target = scope[0], scope[1]
        if isinstance(token, list):
            total = 0.0
            for key, _op, value in token:
                if key == "value":
                    total = self.value(value, scope)
                elif key == "add":
                    total += self.value(value, scope)
                elif key == "subtract":
                    total -= self.value(value, scope)
                elif key == "divide":
                    total /= self.value(value, scope)
                elif key == "if":
                    limit = next(v for k, _o, v in value if k == "limit")
                    if self.trigger(limit, scope):
                        total = self.value([("value", "=", repr(total))] + [i for i in value if i[0] != "limit"],
                                           scope)
                elif key == "every_scope_building":
                    limit = next((v for k, _o, v in value if k == "limit"), [])
                    for site in target.sites:
                        if self.trigger(limit, ("building", site)):
                            total = self.value([("value", "=", repr(total))] + [i for i in value if i[0] != "limit"],
                                               ("building", site))
                else:
                    raise AssertionError("the model does not know the value key %r" % key)
            return round(total, 5)
        if token == PURCHASE:
            return target.purchase
        if token == "level":
            assert kind == "building", "level read outside a building"
            return float(target.level)
        if token == "modifier:country_construction_add":
            assert kind == "country"
            return target.delivered()
        if token.startswith("var:"):
            return target.get(token[4:])
        if token in self.world.values:
            assert kind == "country", "%s read outside a country" % token
            return self.value(self.world.values[token], scope)
        if token == "yes":
            return True
        return float(token)

    # ------------------------------------------------------------ triggers
    def trigger(self, items, scope):
        return all(self.one(key, op, value, scope) for key, op, value in items)

    def one(self, key, op, value, scope):
        kind, target = scope[0], scope[1]
        if key == "NOT":
            return not any(self.one(k, o, v, scope) for k, o, v in value)
        if key == "OR":
            return any(self.one(k, o, v, scope) for k, o, v in value)
        if key == "AND":
            return self.trigger(value, scope)
        if key == "occupancy":
            assert kind == "building", "occupancy read outside a building"
            return compare(target.occupancy, op, float(value))
        if key == "level":
            assert kind == "building", "level read outside a building"
            return compare(target.level, op, float(value))
        if key == "is_building_type":
            assert kind == "building"
            return value == SITE
        if key == "is_ai":
            assert kind == "country"
            return target.ai == (value == "yes")
        if key == "has_variable":
            assert kind in ("country", "state"), "a %s has no variables" % kind
            return target.has(value)
        if key == "has_global_variable":
            return value in self.world.globals
        if key == "has_modifier":
            if kind == "building":
                assert value == CAPACITY
                return target.capacity is not None
            raise AssertionError("has_modifier on a %s: it does not see a modifier added or removed earlier "
                                 "in the same effect, so the crew's state lives in variables" % kind)
        if key == "state":
            assert kind == "building", "state link outside a building"
            return self.trigger(value, ("state", target.state))
        if key == "owner":
            assert kind == "building", "owner link outside a building"
            return self.trigger(value, ("country", target.country))
        if key == "any_scope_building":
            assert kind == "country"
            return any(self.trigger(value, ("building", site)) for site in target.sites)
        if key.startswith("var:"):
            if not target.has(key[4:]):
                if op == "?=":
                    return False
                raise AssertionError("var:%s compared while unset" % key[4:])
            return compare(target.get(key[4:]), op, self.value(value, scope))
        if key in self.world.values or key == PURCHASE:
            return compare(self.value(key, scope), op, self.value(value, scope))
        raise AssertionError("the model does not know the trigger %r" % key)

    # ------------------------------------------------------------ effects
    def effect(self, items, scope):
        kind, target = scope[0], scope[1]
        taken = True  # whether the last if / else_if of this block ran
        for key, _op, value in items:
            if key == "if":
                taken = self.trigger(next(v for k, _o, v in value if k == "limit"), scope)
                if taken:
                    self.effect([i for i in value if i[0] != "limit"], scope)
            elif key == "else_if":
                if not taken:
                    taken = self.trigger(next(v for k, _o, v in value if k == "limit"), scope)
                    if taken:
                        self.effect([i for i in value if i[0] != "limit"], scope)
            elif key == "else":
                if not taken:
                    self.effect(value, scope)
                taken = True
            elif key == "every_scope_building":
                assert kind == "country"
                limit = next((v for k, _o, v in value if k == "limit"), [])
                for site in list(target.sites):
                    if self.trigger(limit, ("building", site)):
                        self.effect([i for i in value if i[0] != "limit"], ("building", site))
            elif key == "state":
                assert kind == "building", "state link outside a building"
                self.effect(value, ("state", target.state))
            elif key == "owner":
                assert kind == "building", "owner link outside a building"
                self.effect(value, ("country", target.country))
            elif key == "set_variable":
                assert kind in ("country", "state"), "a %s has no variables" % kind
                if isinstance(value, str):
                    target.vars[value] = (True, None)
                else:
                    fields = {k: v for k, _o, v in value}
                    amount = self.value(fields["value"], scope) if "value" in fields else True
                    until = self.world.day + int(fields["days"]) if "days" in fields else None
                    target.vars[fields["name"]] = (amount, until)
            elif key == "change_variable":
                fields = {k: v for k, _o, v in value}
                target.vars[fields["name"]] = (target.get(fields["name"]) + float(fields["add"]), None)
            elif key == "remove_variable":
                assert kind in ("country", "state"), "a %s has no variables" % kind
                if not target.has(value):
                    self.world.errors.append("remove_variable of unset %s" % value)
                target.vars.pop(value, None)
            elif key == "set_global_variable":
                fields = {k: v for k, _o, v in value} if isinstance(value, list) else {"name": value}
                self.world.globals[fields["name"]] = True
            elif key == "add_modifier":
                fields = {k: v for k, _o, v in value}
                if kind == "state":
                    target.modifiers.append(fields["name"])
                elif kind == "building":
                    assert fields["name"] == CAPACITY
                    if target.capacity is not None:
                        self.world.errors.append("a second copy of the capacity modifier")
                    multiplier = fields["multiplier"]
                    # The engine keeps the expression and reads it again on later ticks.
                    target.capacity = multiplier[len("owner.var:"):] if multiplier.startswith("owner.var:") \
                        else float(multiplier)
                # A country's modifier (the private share) is not part of this model.
            elif key == "remove_modifier":
                if kind == "state":
                    if value not in target.modifiers:
                        self.world.errors.append("remove_modifier of absent %s" % value)
                    else:
                        target.modifiers.remove(value)
                elif kind == "building":
                    assert value == CAPACITY
                    if target.capacity is None:
                        self.world.errors.append("remove_modifier of an absent capacity modifier")
                    target.capacity = None
            elif key == "debug_log":
                self.world.log.append(value.strip('"'))
            elif key == "debug_log_scopes":
                pass
            elif key in self.world.effects and value == "yes":
                self.effect(self.world.effects[key], scope)
            else:
                raise AssertionError("the model does not know the effect %r" % key)


ORDERS = (True, False)  # the weekly hiring before the weekly pulse, and after it
SURPLUS = ("at_once", "weekly", "never")


def worlds(**kwargs):
    for surplus, hiring_first in itertools.product(SURPLUS, ORDERS):
        yield surplus, hiring_first, World(surplus=surplus, **kwargs)


class NeverMoreThanThePurchase(unittest.TestCase):
    """The requirement that outranks the rest: whatever the engine does, no week delivers a multiple of the
    purchase. A site waiting for its first laborer may add its level's tenth of a point when it hires."""

    def watch(self, world, country, weeks, hiring_first, slack=0.0, press=()):
        for week in range(weeks):
            world.day += 7
            steps = [world.employment, lambda: world.pulse(country)]
            for step in (steps if hiring_first else steps[::-1]):
                step()
                self.assertLessEqual(country.delivered(), country.purchase + slack + ROUNDING,
                                     "week %d, surplus %s, hiring first %s" % (week, world.surplus, hiring_first))
            if week in press:
                world.day += 1
                world.button(country)
                self.assertLessEqual(country.delivered(), country.purchase + slack + ROUNDING, "after the button")
                world.day -= 1
        self.assertEqual(world.errors, [])

    def test_new_sites_beside_an_established_one(self):
        for surplus, hiring_first, world in worlds():
            with self.subTest(surplus=surplus, hiring_first=hiring_first):
                country = Country(world)
                country.site()
                self.watch(world, country, 3, hiring_first)
                for _ in range(5):
                    country.site()
                # Five sites each taking their first laborer of ten: a tenth of a point each, not a share each.
                self.watch(world, country, 4, hiring_first, slack=5 * HIRING_RATE)
                self.assertAlmostEqual(country.delivered(), country.purchase, places=4)

    def test_a_save_from_before_the_crew(self):
        # Every site holds up to ten laborers on its ten jobs and carries the old sizing's modifier.
        for surplus, hiring_first, world in worlds():
            with self.subTest(surplus=surplus, hiring_first=hiring_first):
                country = Country(world, purchase=120.0)
                for laborers in (10, 10, 7, 4, 2, 1, 0):
                    site = country.site(laborers=laborers)
                    site.capacity = "te_cm_capacity_mult"
                country.vars["te_cm_capacity_mult"] = (120.0 / 7 - 1, None)  # #1770: the purchase over all levels
                self.watch(world, country, 14, hiring_first, slack=HIRING_RATE, press=(0, 1, 5))

    def test_a_direct_games_staff_on_a_market_site(self):
        # A level-1 site kept through the switch back to the market holds a sector's workforce on ten jobs.
        for surplus, hiring_first, world in worlds():
            with self.subTest(surplus=surplus, hiring_first=hiring_first):
                country = Country(world)
                country.site(laborers=4800)
                country.site(laborers=1)
                # From the first pass that sees it. What such a site delivers before that, at the engine's
                # own throughput, is the switch's business (te_direct_construction_revert_all).
                world.pulse(country)
                self.watch(world, country, 8, hiring_first)

    def test_a_site_that_hires_twice_before_it_is_cut(self):
        # Two laborers on the one job the cut leaves: 200% staffed.
        for surplus, hiring_first, world in worlds():
            with self.subTest(surplus=surplus, hiring_first=hiring_first):
                country = Country(world)
                country.site(laborers=2)
                self.watch(world, country, 6, hiring_first)

    def test_sites_of_several_levels(self):
        for surplus, hiring_first, world in worlds():
            with self.subTest(surplus=surplus, hiring_first=hiring_first):
                country = Country(world)
                country.site(level=7)
                country.site(level=2, laborers=3)  # three of twenty: more than its first hires
                country.site(level=5, laborers=1)  # one of fifty: fewer
                self.watch(world, country, 12, hiring_first, slack=3 * HIRING_RATE * 7)

    def test_a_cut_that_does_nothing(self):
        # The unverified engine fact: the state's modifier may not change a site's jobs on 1.15.1.
        for surplus, hiring_first, world in worlds(inert_cut=True):
            with self.subTest(surplus=surplus, hiring_first=hiring_first):
                country = Country(world)
                for laborers in (0, 0, 3, 10):
                    country.site(laborers=laborers)
                self.watch(world, country, 14, hiring_first, slack=2 * HIRING_RATE)

    def test_a_site_over_its_jobs_is_never_sized(self):
        # Seen at a pass, a site above 105% carries no share: its throughput is -100% until it is back.
        world = World(surplus="never")
        country = Country(world)
        site = country.site()
        for _ in range(2):
            world.week()
        self.assertTrue(site.crewed)
        site.laborers = 3
        world.pulse(country)
        self.assertFalse(site.crewed)
        self.assertEqual(site.delivers(), 0)
        self.assertEqual(world.errors, [])


class TheCrew(unittest.TestCase):
    """What a site goes through."""

    def test_a_new_site_is_full_from_its_first_hire(self):
        for surplus, hiring_first, world in worlds():
            with self.subTest(surplus=surplus, hiring_first=hiring_first):
                country = Country(world)
                site = country.site()
                for _ in range(2):
                    world.week(hiring_first)
                # At most two weeks: its first hire, and the pulse after it.
                self.assertEqual((site.laborers, site.jobs), (1, 1))
                self.assertTrue(site.crewed)
                self.assertAlmostEqual(country.delivered(), country.purchase, places=4)
                self.assertEqual(site.state.modifiers, [CREW_MODIFIER])
                for _ in range(10):
                    world.week(hiring_first)
                    world.button(country)
                self.assertEqual(site.state.modifiers, [CREW_MODIFIER])  # never a second copy
                self.assertAlmostEqual(country.delivered(), country.purchase, places=4)
                self.assertEqual(world.errors, [])

    def test_before_the_cut_a_site_would_take_ten_weeks(self):
        # What the cut is for. With the modifier doing nothing a site hires its one laborer in ten a week.
        world = World(inert_cut=True)
        country = Country(world)
        site = country.site()
        for week in range(1, 11):
            world.week()
            self.assertEqual(site.laborers, week)
        self.assertEqual(site.occupancy, 1.0)

    def test_a_site_that_loses_its_laborer_hires_again(self):
        # A cut site holds one job and may hire a tenth of a laborer a week: nothing. With no laborer the
        # cut goes, it has ten jobs, and it hires one.
        for surplus, hiring_first, world in worlds():
            with self.subTest(surplus=surplus, hiring_first=hiring_first):
                country = Country(world)
                site = country.site()
                for _ in range(3):
                    world.week(hiring_first)
                site.laborers = 0
                world.employment()
                self.assertEqual(site.laborers, 0)  # stuck while the cut stands
                for _ in range(3):
                    world.week(hiring_first)
                self.assertEqual((site.laborers, site.jobs), (1, 1))
                self.assertTrue(site.crewed)
                self.assertEqual(world.errors, [])

    def test_a_site_that_cannot_hire_is_never_marked(self):
        world = World(labor=0)
        country = Country(world)
        site = country.site()
        for _ in range(6):
            world.week()
        self.assertFalse(site.crewed)
        self.assertEqual(site.state.modifiers, [])
        self.assertEqual(country.delivered(), 0)

    def test_an_old_saves_sites_are_cut_and_counted_once_the_surplus_is_gone(self):
        # Owner, 2026-11-13: the engine lets the laborers above a cut site's jobs go.
        for surplus in ("at_once", "weekly"):
            for hiring_first in ORDERS:
                with self.subTest(surplus=surplus, hiring_first=hiring_first):
                    world = World(surplus=surplus)
                    country = Country(world, purchase=80.0)
                    sites = [country.site(laborers=laborers) for laborers in (10, 8, 5, 3, 2)]
                    world.week(hiring_first)
                    # Cut at the first pulse, and not counted while they may hold more laborers than jobs.
                    self.assertTrue(all(site.state.modifiers == [CREW_MODIFIER] for site in sites))
                    self.assertFalse(any(site.crewed for site in sites))
                    self.assertEqual(country.delivered(), 0)
                    for _ in range(2):
                        world.week(hiring_first)
                    self.assertTrue(all(site.crewed and (site.laborers, site.jobs) == (1, 1) for site in sites))
                    self.assertAlmostEqual(country.delivered(), 80.0, places=4)
                    self.assertEqual(len(world.lines("construction_site_surplus")), 1)
                    self.assertIn("TE_SELF_CHECK OK construction_site_surplus", world.lines("construction_site_surplus")[0])
                    self.assertEqual(world.errors, [])

    def test_if_the_engine_keeps_the_surplus_the_cut_comes_off(self):
        for hiring_first in ORDERS:
            with self.subTest(hiring_first=hiring_first):
                world = World(surplus="never")
                country = Country(world, purchase=80.0)
                sites = [country.site(laborers=laborers) for laborers in (10, 5, 3)]
                for _ in range(4):
                    world.week(hiring_first)
                    self.assertLessEqual(country.delivered(), 80.0 + ROUNDING)
                # Uncut, on their ten jobs, counted, and filling at one laborer a week as before the crew.
                self.assertTrue(all(site.state.modifiers == [] and site.crewed for site in sites))
                lines = world.lines("construction_site_surplus")
                self.assertEqual(len(lines), 1, lines)
                self.assertTrue(lines[0].startswith("TE_SELF_CHECK BROKEN construction_site_surplus"))
                for _ in range(8):
                    world.week(hiring_first)
                    self.assertLessEqual(country.delivered(), 80.0 + ROUNDING)
                self.assertEqual([site.laborers for site in sites], [10, 10, 10])
                self.assertAlmostEqual(country.delivered(), 80.0, places=4)
                self.assertEqual(world.errors, [])

    def test_the_purchase_buttons_read_nothing_off_a_site(self):
        # A button can size the sites the day after a cut, before the engine has done anything about it.
        world = World(surplus="weekly")
        country = Country(world, purchase=80.0)
        sites = [country.site(laborers=laborers) for laborers in (5, 1)]
        world.week()
        for day in range(1, 7):
            world.day += 1
            world.button(country)
            self.assertFalse(sites[0].crewed, "day %d" % day)
            self.assertEqual(world.lines("construction_site_surplus"), [])
            self.assertEqual(world.lines("construction_site_crew"), [])
        self.assertEqual(world.errors, [])


class TheSelfChecks(unittest.TestCase):
    def test_the_crew_check_says_whether_the_cut_took(self):
        for inert, verdict in ((False, "OK"), (True, "BROKEN")):
            for hiring_first in ORDERS:
                with self.subTest(inert=inert, hiring_first=hiring_first):
                    world = World(inert_cut=inert)
                    country = Country(world)
                    country.site()
                    country.site()
                    for _ in range(6):
                        world.week(hiring_first)
                    lines = world.lines("construction_site_crew")
                    self.assertEqual(len(lines), 1, lines)  # once a game
                    self.assertTrue(lines[0].startswith("TE_SELF_CHECK %s construction_site_crew" % verdict))

    def test_the_crew_check_does_not_read_a_site_of_several_levels(self):
        # A level-5 site cut at one laborer of fifty sits at one of five: a fifth staffed with the cut working.
        world = World()
        country = Country(world)
        country.site(level=5, laborers=1)
        for _ in range(4):
            world.week()
        self.assertEqual(world.lines("construction_site_crew"), [])

    def test_the_surplus_check_is_silent_when_the_cut_does_nothing(self):
        # With the cut not taking, a site that held five laborers reads six of ten a week later: that says
        # nothing about what the engine does with a surplus, and the crew check is the one that reports it.
        world = World(inert_cut=True)
        country = Country(world)
        country.site(laborers=5)
        for _ in range(4):
            world.week()
        self.assertEqual(world.lines("construction_site_surplus"), [])

    def test_the_delivery_check_reads_a_full_week(self):
        for hiring_first in ORDERS:
            with self.subTest(hiring_first=hiring_first):
                world = World()
                country = Country(world, purchase=100.0)
                country.site()
                country.site()
                for _ in range(6):
                    world.week(hiring_first)
                lines = world.lines("construction_site_delivery")
                self.assertEqual(len(lines), 1, lines)
                self.assertTrue(lines[0].startswith("TE_SELF_CHECK OK construction_site_delivery"))

    def test_the_delivery_check_is_once_a_game_and_for_ai_countries(self):
        world = World()
        player = Country(world, purchase=100.0, ai=False)
        player.site()
        for _ in range(6):
            world.week()
        self.assertEqual(world.lines("construction_site_delivery"), [])
        for _ in range(2):
            Country(world, purchase=100.0).site()
        for _ in range(8):
            world.week()
        self.assertEqual(len(world.lines("construction_site_delivery")), 1)

    def test_a_week_in_which_a_crewed_site_went_or_lost_its_laborer_decides_nothing(self):
        for what in ("removed", "emptied"):
            with self.subTest(what=what):
                world = World()
                country = Country(world, purchase=100.0)
                sites = [country.site(), country.site()]
                world.week()  # each hires, is cut and sized, and the country stores its purchase
                self.assertEqual(world.lines("construction_site_delivery"), [])
                self.assertTrue(country.has("te_cm_chk_target"))
                if what == "removed":
                    # te_construction_market_state_on_end_market: the building goes, then the crew.
                    country.sites.remove(sites[1])
                    world.run("te_construction_market_clear_crew", ("state", sites[1].state))
                else:
                    sites[1].laborers = 0
                world.day += 7
                world.pulse(country)
                # Half the purchase was delivered that week, and it is not called BROKEN.
                self.assertEqual(world.lines("construction_site_delivery"), [])
                for _ in range(4):
                    world.week()
                lines = world.lines("construction_site_delivery")
                self.assertEqual(len(lines), 1)
                self.assertTrue(lines[0].startswith("TE_SELF_CHECK OK"))

    def test_the_delivery_check_says_broken_when_the_sites_are_sized_wrong(self):
        world = World()
        country = Country(world, purchase=100.0)
        country.site()
        world.week()
        self.assertTrue(country.has("te_cm_chk_target"))
        # The yardstick is the stored purchase: a sizing that gave the sites half of it is BROKEN.
        country.vars["te_cm_capacity_mult"] = (49.0, None)
        world.week()
        lines = world.lines("construction_site_delivery")
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("TE_SELF_CHECK BROKEN construction_site_delivery"))

    def test_a_game_whose_sites_never_get_a_crew_gets_a_verdict(self):
        # With no crewed site anywhere the delivery check never arms, so that failure would give no line.
        world = World(labor=0)
        country = Country(world, purchase=100.0)
        country.site()
        for week in range(1, 7):
            world.week()
            self.assertEqual(len(world.lines("construction_site_unstaffed")), 1 if week >= 4 else 0, week)
        self.assertEqual(world.lines("construction_site_delivery"), [])

    def test_no_such_verdict_in_a_game_that_works(self):
        world = World()
        for _ in range(3):
            Country(world, purchase=100.0).site()
        for _ in range(12):
            world.week()
        self.assertEqual(world.lines("construction_site_unstaffed"), [])
        self.assertEqual(world.errors, [])


class TheNumbers(unittest.TestCase):
    def test_the_cut_leaves_exactly_the_first_weeks_hires(self):
        market = body_of(code(PMS), "pm_te_construction_market_base")
        jobs = float(re.search(r"level_scaled\s*=\s*\{\s*building_employment_laborers_add\s*=\s*([\d.]+)\s*\}",
                               market).group(1))
        cut = float(re.search(r"%s\s*=\s*(-[\d.]+)" % EMPLOYEE_MULT,
                              body_of(code(MODIFIERS), CREW_MODIFIER)).group(1))
        # A building hires a tenth of its jobs a week; the cut must leave exactly that many jobs, or the site
        # is under-staffed (too few cut) or holds more laborers than jobs (too many).
        self.assertAlmostEqual(jobs * (1 + cut), jobs * HIRING_RATE, places=6)
        self.assertGreaterEqual(jobs * HIRING_RATE, 1)  # at least one whole laborer to hire
        self.assertEqual(jobs, 10)  # the model above places a site with ten jobs a level
        # The engine ignores a modifier name nothing registers.
        self.assertRegex(code(MODIFIER_TYPES), r"(?m)^%s\s*=\s*\{" % EMPLOYEE_MULT)

    def test_the_job_attractiveness_stays_on_the_market_method(self):
        pms = code(PMS)
        market = body_of(pms, "pm_te_construction_market_base")
        self.assertRegex(market, r"unscaled\s*=\s*\{\s*building_job_attractiveness_mult\s*=\s*5\s*\}")
        # Not the direct methods: there the site is a sector with a real workforce.
        self.assertEqual(pms.count("building_job_attractiveness_mult"), 1)

    def test_the_values_read_no_staffing(self):
        # Owner, 2026-11-13: no scaling with employment. The values count the sites the crew pass has marked.
        text = code(VALUES)
        self.assertNotIn("occupancy", text)
        self.assertNotIn("has_employee_slots_filled", text)
        self.assertIn("has_variable = %s" % CREW_MARK, text)

    def test_crewed_sites_of_any_level_deliver_the_purchase(self):
        for levels, purchase in itertools.product(((1,), (1, 1), (7,), (7, 1), (1,) * 5), (0.5, 50.0, 5000.0)):
            with self.subTest(levels=levels, purchase=purchase):
                world = World()
                country = Country(world, purchase=purchase)
                for level in levels:
                    country.site(level=level)
                for _ in range(3):
                    world.week()
                self.assertAlmostEqual(country.delivered(), purchase, places=2)

    def test_no_site_and_no_purchase(self):
        world = World()
        country = Country(world)
        world.week()
        self.assertEqual(country.get("te_cm_capacity_mult"), 0)
        nothing = Country(world, purchase=0.0)
        nothing.site()
        for _ in range(3):
            world.week()
        # No purchase: throughput -100%, so the site delivers, and buys, nothing.
        self.assertEqual(nothing.delivered(), 0)


class TheScriptAsText(unittest.TestCase):
    """What the model above does not run: the walk's shape, and where the crew is cleared."""

    def setUp(self):
        self.text = code(EFFECTS)
        self.body = body_of(self.text, "te_construction_market_apply_per_site_modifier")

    def test_every_site_reads_one_country_value(self):
        # One value, written once before the walk that adds the modifier: a per-site value in a shared
        # country variable let every site re-read the last site's between pulses.
        self.assertEqual(len(re.findall(r"name\s*=\s*te_cm_capacity_mult", self.body)), 1)
        self.assertLess(self.body.index("te_construction_market_site_crew = yes"),
                        self.body.index("te_cm_capacity_mult"))
        self.assertLess(self.body.index("te_cm_capacity_mult"), self.body.rindex("every_scope_building"))
        self.assertRegex(self.body, r"value\s*=\s*%s\b" % THROUGHPUT)
        self.assertRegex(self.body, r"multiplier\s*=\s*owner\.var:te_cm_capacity_mult")
        # The engine re-evaluates the multiplier expression on later ticks.
        self.assertNotIn("remove_variable = te_cm_capacity_mult", self.body)

    def test_the_crews_state_is_never_asked_of_has_modifier(self):
        # has_modifier does not see a modifier added or removed earlier in the same effect.
        for name in ("te_construction_market_site_crew", "te_construction_market_clear_crew",
                     "te_construction_market_add_crew_cut", "te_construction_market_remove_crew_cut"):
            self.assertNotIn("has_modifier", body_of(self.text, name), name)
        self.assertNotIn("has_modifier = %s" % CREW_MODIFIER, code(DIRECT))
        self.assertNotIn("has_modifier = %s" % CREW_MODIFIER, code(PLACEMENT))
        # The modifier and its variable go on and come off in one place each.
        self.assertEqual(self.text.count("name = %s" % CREW_MODIFIER), 1)
        self.assertEqual(self.text.count("remove_modifier = %s" % CREW_MODIFIER), 1)

    def test_no_building_is_removed_or_made_by_the_crew_pass(self):
        # The other mod resets an over-staffed site by removing and re-creating it inside the walk over the
        # country's buildings. This one only moves a state's modifier and variables.
        for name in ("te_construction_market_site_crew", "te_construction_market_clear_crew",
                     "te_construction_market_apply_per_site_modifier"):
            body = body_of(self.text, name)
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
        # The recalc after a border change: a site it makes, or makes again at level 1, starts without a crew,
        # and every site it places in a capital goes through te_construction_market_place_site.
        recalc = flat(body_of(self.text, "te_construction_market_country_update_sites"))
        self.assertIn("if = { limit = { NOT = { has_building = %s } } te_construction_market_clear_crew = yes } "
                      "else_if = { limit = { NOT = { b:%s.level = 1 } } te_construction_market_clear_crew = yes } "
                      "te_construction_market_set_specified_level = {" % (SITE, SITE), recalc)
        self.assertNotIn("create_building", recalc)
        direct = code(DIRECT)
        self.assertRegex(flat(body_of(direct, "te_direct_construction_convert_state")),
                         r"^te_direct_construction_convert_state = \{ te_construction_market_clear_crew = yes ")
        # Every state of every country on the switch to direct construction, not only the converted ones.
        self.assertIn("every_scope_state = { te_construction_market_clear_crew = yes } every_scope_state = { "
                      "limit = { any_scope_building = {",
                      flat(body_of(direct, "te_direct_construction_convert_all")))
        # And the switch's self-check counts a state that kept it, by the variable.
        self.assertIn("limit = { te_free_market_construction_off = yes has_variable = te_cm_site_crew_cut } "
                      "change_global_variable = { name = te_dc_check_stale add = 1 }",
                      flat(body_of(direct, "te_direct_construction_switch_self_check")))

    def test_the_delivery_check_reads_before_the_sizing_and_arms_after_it(self):
        pulse = flat(body_of(self.text, "te_construction_market_country_update_data"))
        self.assertRegex(pulse, r"te_cm_site_delivery_selfcheck = yes .*"
                                r"set_variable = te_cm_weekly_pass "
                                r"te_construction_market_apply_per_site_modifier = yes "
                                r"remove_variable = te_cm_weekly_pass .*"
                                r"te_cm_site_delivery_selfcheck_arm = yes")
        # A marker of its own: a game that had the first version's verdict gets this check too.
        self.assertNotIn("te_cm_site_delivery_check_done", self.text)


if __name__ == "__main__":
    unittest.main()
