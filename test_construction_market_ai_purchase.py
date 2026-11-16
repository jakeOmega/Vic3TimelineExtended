"""What an AI government buys a week in a market game (te_construction_market_ai_purchase_target).

common/script_values/te_construction_market_ai_values.txt sets the purchase: the country's budget surplus over the
smoothed price, scaled by reserves and debt, or a floor if that is more, capped by the government queue. Until
2026-11-15 the floor was 10 points a week for every country, which was more than the whole weekly income of 23 of the
28 AI countries buying in February 1836; they borrowed to the engine's construction pause within months. The floor is
now a twentieth of fixed income, never more than the 10 points it was, paid from reserves (a tenth of itself with
none), plus a fifth of fixed income while the country is short of bureaucracy
(docs/systems/mod_systems/construction.md, "The AI's purchase").

Nothing in the engine checks that script, so this runs the script's own text through the evaluator of
test_construction_market_budget_step.py, with the engine's reads (income, debt, reserves, the queue) stubbed, and
compares it with a model written apart from the script. It also holds the script's constants to the engine defines they
are taken from, and works the long-run comparison with the rule before: a country that borrows to the pause, waits and
pays interest, against one that spends what it has.

Run: python3 -m unittest test_construction_market_ai_purchase -v
"""
import itertools
import json
import math
import re
import unittest
from pathlib import Path

from test_construction_market_budget_step import CURRENT_VALUES, DISPLAY_VALUES, TARGET_VALUES, Env, load

ROOT = Path(__file__).resolve().parent
AI_VALUES = ROOT / "common/script_values/te_construction_market_ai_values.txt"
PULSE = ROOT / "common/scripted_effects/te_construction_market_pulse_effects.txt"
AI_EFFECTS = ROOT / "common/scripted_effects/te_construction_market_ai_effects.txt"
DEFINES_DIR = ROOT / "common/defines"
SYSTEM_DOC = ROOT / "docs/systems/mod_systems/construction.md"
AI_DOC = ROOT / "docs/systems/mod_systems/ai.md"
PLAYTEST = ROOT / "docs/testing/ai-economy-playtest.md"
PROBE_KEY = ROOT / "scripts/analysis/ai_probe_key.json"

# The rule, restated here so the script is checked against something that is not itself.
FLOOR_INCOME_SHARE = 0.05
FLOOR_MAX_POINTS = 10.0
FLOOR_FULL_RESERVES = 0.1
FLOOR_MIN_FACTOR = 0.1
BUREAUCRACY_INCOME_SHARE = 0.2

# The engine's AI defines the constants are taken from (vanilla 1.15.1, common/defines/00_ai.txt). The mod must leave
# them alone for the reasoning to hold; test_matches_the_game_files reads them where the game is installed.
NAI = {
    "CONSTRUCTION_DEBT_PAUSE": 0.4,
    "CONSTRUCTION_DEBT_RESUME": 0.2,
    "CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS": 0.1,
    "WAGE_CUT_INCOME_RATIO_THRESHOLD": 1.05,
    "MONEY_SPENDING_MAX_RATIO_TO_REMOVE_SHOULD_HAVE": 1.05,
}

_PARSED = {}


def _parsed():
    if not _PARSED:
        constants, values = {}, {}
        for path in (TARGET_VALUES, CURRENT_VALUES, DISPLAY_VALUES, AI_VALUES):
            c, v = load(path)
            constants.update(c)
            values.update(v)
        _PARSED["constants"], _PARSED["values"] = constants, values
    return _PARSED["constants"], _PARSED["values"]


class AiEnv(Env):
    """The shared evaluator with the AI values file loaded too, and the files parsed once."""

    def __init__(self, names, variables, flags):
        self.memo = {}
        self.constants, self.values = _parsed()
        self.names, self.variables, self.flags, self.triggers = names, variables, flags, {}


class Country:
    """One week of one AI government, as the script reads it."""

    def __init__(self, fixed_income, surplus, price=1250.0, reserves=0.0, debt=0.0, bureaucracy=50.0, queued=1,
                 weekly_max=20.0, paused=False, at_war=False, bubble=None, income=None):
        self.fixed_income = float(fixed_income)
        self.surplus = float(surplus)  # net_fixed_income
        self.price = float(price)  # var:te_construction_market_price_stabilizer
        self.reserves, self.debt = reserves, debt  # scaled_gold_reserves, scaled_debt
        self.bureaucracy, self.queued, self.weekly_max = bureaucracy, queued, weekly_max
        self.paused, self.at_war, self.bubble = paused, at_war, bubble
        self.income = float(fixed_income if income is None else income)

    def env(self):
        names = {
            "net_fixed_income": self.surplus,
            "fixed_income": self.fixed_income,
            "scaled_gold_reserves": self.reserves,
            "scaled_debt": self.debt,
            "bureaucracy": self.bureaucracy,
            "construction_queue_num_queued_government_levels": float(self.queued),
            "modifier:country_max_weekly_construction_progress_add": self.weekly_max,
        }
        variables = {"te_construction_market_price_stabilizer": self.price}
        if self.bubble is not None:
            variables["bubble_pressure"] = self.bubble
        return AiEnv(names, variables, flags={"is_construction_paused": self.paused, "is_at_war": self.at_war})

    def script(self):
        return self.env().value("te_construction_market_ai_purchase_target")

    def script_floor(self):
        return self.env().value("te_construction_market_ai_purchase_floor")

    def bill(self):
        return self.script() * self.price


def model_factor(c):
    factor = 1 + c.reserves - c.debt
    if c.at_war and c.reserves < 0.5:
        factor -= 0.5 - c.reserves
    if c.bubble is not None and c.bubble >= 50 and c.reserves < 0.3:
        factor -= 0.3 - c.reserves
    return max(factor, 0.1)


def model_floor(c):
    floor = min(FLOOR_MAX_POINTS, FLOOR_INCOME_SHARE * c.fixed_income / c.price)
    floor *= max(FLOOR_MIN_FACTOR, min(1.0, c.reserves / FLOOR_FULL_RESERVES))
    if c.bureaucracy < 0:
        floor += BUREAUCRACY_INCOME_SHARE * c.fixed_income / c.price
    return floor


def model(c):
    if c.paused or c.queued <= 0:
        return 0.0
    points = max(max(c.surplus, 0.0) / c.price * model_factor(c), model_floor(c))
    return min(points, c.queued * c.weekly_max)


def before(c):
    """The rule until 2026-11-15, for the comparisons: a floor of 10 points, more when short of bureaucracy (a fifth
    of income over the price clamped to 50-150), whole points."""
    if c.paused or c.queued <= 0:
        return 0.0
    floor = 10.0
    if c.bureaucracy < 0:
        floor += c.income / min(max(c.price, 50.0), 150.0) / 5
    points = float(math.floor(max(max(c.surplus, 0.0) / c.price * model_factor(c), floor) + 0.5))
    return min(points, c.queued * c.weekly_max)


# Economies by weekly fixed income, each at a smoothed price the probe's 1836 run showed for one like it (Kunduz,
# Bavaria, the United States), and a late-game great power at a late-game price.
ECONOMIES = {"tiny": (857.0, 1249.0), "mid": (13678.0, 1265.0), "large": (75817.0, 1256.0), "huge": (3500000.0, 6000.0)}
# What the script's five-decimal arithmetic can differ by from the model's, in points.
STEP = 0.001


class Constants(unittest.TestCase):
    def test_the_script_holds_the_rule_this_file_models(self):
        constants, _ = _parsed()
        self.assertEqual(constants["TE_CONSTRUCTION_MARKET_AI_FLOOR_INCOME_SHARE"], FLOOR_INCOME_SHARE)
        self.assertEqual(constants["TE_CONSTRUCTION_MARKET_AI_FLOOR_MAX_POINTS"], FLOOR_MAX_POINTS)
        self.assertEqual(constants["TE_CONSTRUCTION_MARKET_AI_FLOOR_FULL_RESERVES"], FLOOR_FULL_RESERVES)
        self.assertEqual(constants["TE_CONSTRUCTION_MARKET_AI_FLOOR_MIN_FACTOR"], FLOOR_MIN_FACTOR)
        self.assertEqual(constants["TE_CONSTRUCTION_MARKET_AI_BUREAUCRACY_INCOME_SHARE"], BUREAUCRACY_INCOME_SHARE)

    def test_the_floor_is_the_margin_the_engines_budget_ai_defends(self):
        # Income under 1.05 times expenses is where it cuts wages and should-have spending: a surplus of 1 - 1/1.05,
        # 4.8% of income.
        for name in ("WAGE_CUT_INCOME_RATIO_THRESHOLD", "MONEY_SPENDING_MAX_RATIO_TO_REMOVE_SHOULD_HAVE"):
            self.assertAlmostEqual(FLOOR_INCOME_SHARE, 1 - 1 / NAI[name], delta=0.005, msg=name)

    def test_the_floor_is_whole_at_the_reserves_the_engine_asks_before_it_queues(self):
        self.assertEqual(FLOOR_FULL_RESERVES, NAI["CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS"])

    def test_the_part_on_credit_is_a_two_hundredth_of_income(self):
        self.assertAlmostEqual(FLOOR_INCOME_SHARE * FLOOR_MIN_FACTOR, 0.005)

    def test_the_mod_leaves_those_defines_at_the_engines_values(self):
        # A mod define that moves one of them moves what the formula's constants stand on: revisit both together.
        for path in sorted(DEFINES_DIR.glob("*.txt")):
            text = "\n".join(line.split("#", 1)[0] for line in path.read_text(encoding="utf-8-sig").splitlines())
            for name in NAI:
                self.assertIsNone(re.search(rf"\b{name}\s*=", text), f"{path.name} sets {name}")

    def test_matches_the_game_files(self):
        path = _game_file("defines/00_ai.txt")
        if path is None:
            self.skipTest("no Victoria 3 install")
        text = path.read_text(encoding="utf-8-sig")
        for name, value in NAI.items():
            m = re.search(rf"^\s*{name}\s*=\s*([0-9.]+)", text, re.M)
            self.assertIsNotNone(m, name)
            self.assertEqual(float(m.group(1)), value, name)


class ScriptAgainstModel(unittest.TestCase):
    def test_across_economies_budgets_debt_and_shortages(self):
        count = 0
        for (name, (fixed_income, price)), share, debt, reserves, bureaucracy, at_war, bubble, (queued, weekly) in \
                itertools.product(ECONOMIES.items(), (-0.25, 0.0, 0.03, 0.17, 0.33, 0.7), (0.0, 0.04, 0.1, 0.3, 0.39),
                                  (0.0, 0.04, 0.1, 0.6), (50.0, -5.0), (False, True), (None, 60.0),
                                  ((1, 10.0), (1, 140.0), (4, 20.0))):
            if debt and reserves:
                continue  # a country holds reserves or owes, never both
            c = Country(fixed_income, share * fixed_income, price, reserves, debt, bureaucracy, queued, weekly,
                        at_war=at_war, bubble=bubble)
            count += 1
            with self.subTest(economy=name, surplus=share, debt=debt, reserves=reserves, bureaucracy=bureaucracy,
                              at_war=at_war, bubble=bubble, queue=(queued, weekly)):
                self.assertAlmostEqual(c.script(), model(c), delta=STEP)
        self.assertGreater(count, 2000)

    def test_it_is_not_rounded_to_whole_points(self):
        # Kunduz: a surplus of 143 a week buys a ninth of a point. Whole points made that nothing.
        self.assertAlmostEqual(Country(857.0, 143.0, 1249.0).script(), 143.0 / 1249.0, delta=STEP)
        self.assertNotIn("round", _code(AI_VALUES.read_text(encoding="utf-8-sig")))

    def test_paused_or_with_an_empty_queue_it_buys_nothing(self):
        for kwargs in ({"paused": True}, {"queued": 0}):
            for bureaucracy in (50.0, -50.0):
                with self.subTest(**kwargs, bureaucracy=bureaucracy):
                    self.assertEqual(Country(75817.0, 30000.0, bureaucracy=bureaucracy, **kwargs).script(), 0.0)

    def test_the_queue_caps_it(self):
        self.assertAlmostEqual(Country(75817.0, 60000.0, 1256.0, queued=1, weekly_max=20.0).script(), 20.0, places=6)
        self.assertAlmostEqual(Country(75817.0, 60000.0, 1256.0, queued=2, weekly_max=20.0).script(), 40.0, places=6)
        # Great Britain, February 1836: short of bureaucracy and in deficit, one level queued at 25 a week.
        gbr = Country(146612.0, -4278.0, 1435.0, reserves=0.15, bureaucracy=-92.0, queued=1, weekly_max=25.0,
                      income=156009.0)
        self.assertAlmostEqual(gbr.script(), 25.0, places=6)
        self.assertEqual(before(gbr), 25.0)


class Surplus(unittest.TestCase):
    """Where the surplus buys more than the floor, nothing changed but the rounding."""

    def test_a_large_economy_buys_what_it_did(self):
        # The United States, February 1836: 32 points before, the surplus term.
        usa = Country(75817.0, 32303.0, 1256.0, reserves=0.232, queued=4, weekly_max=20.0, income=79196.0)
        self.assertEqual(before(usa), 32.0)
        self.assertAlmostEqual(usa.script(), 32303.0 / 1256.0 * 1.232, delta=STEP)
        self.assertLess(abs(usa.script() - before(usa)), 0.5)

    def test_with_no_reserves_and_no_debt_it_spends_the_surplus_and_no_more(self):
        for fixed_income, price in ECONOMIES.values():
            for share in (0.006, 0.06, 0.2, 0.5):
                c = Country(fixed_income, share * fixed_income, price, queued=50, weekly_max=140.0)
                with self.subTest(fixed_income=fixed_income, surplus=share):
                    self.assertAlmostEqual(c.bill(), c.surplus, delta=STEP * price)

    def test_reserves_raise_it_and_debt_lowers_it(self):
        base = Country(13678.0, 2793.0, 1265.0).script()
        self.assertGreater(Country(13678.0, 2793.0, 1265.0, reserves=0.5).script(), base)
        self.assertLess(Country(13678.0, 2793.0, 1265.0, debt=0.3).script(), base)

    def test_no_country_buys_more_than_before_beyond_the_rounding(self):
        # At any price over 150, where the old bureaucracy clause's clamp stopped holding its price down.
        for (fixed_income, price), share, debt, reserves, bureaucracy in itertools.product(
                ECONOMIES.values(), (-0.25, 0.0, 0.1, 0.33, 0.7), (0.0, 0.05, 0.2, 0.39), (0.0, 0.4), (50.0, -5.0)):
            if debt and reserves:
                continue
            c = Country(fixed_income, share * fixed_income, price, reserves, debt, bureaucracy, queued=50,
                        weekly_max=140.0)
            with self.subTest(fixed_income=fixed_income, surplus=share, debt=debt, bureaucracy=bureaucracy):
                self.assertLessEqual(c.script(), before(c) + 0.5 + STEP)


class Floor(unittest.TestCase):
    """A government whose surplus buys less than the floor: here, mostly one with no surplus at all."""

    def test_with_reserves_it_costs_a_twentieth_of_fixed_income(self):
        for name in ("tiny", "mid", "large"):
            fixed_income, price = ECONOMIES[name]
            for share, reserves in itertools.product((-0.25, 0.0, 0.03), (0.1, 0.5)):
                c = Country(fixed_income, share * fixed_income, price, reserves=reserves)
                with self.subTest(economy=name, surplus=share, reserves=reserves):
                    self.assertGreaterEqual(c.bill(), FLOOR_INCOME_SHARE * fixed_income - STEP * price)
                    # A surplus of 3% with reserves of a half buys 4.5%, still under the floor.
                    self.assertLessEqual(c.bill(), FLOOR_INCOME_SHARE * fixed_income + STEP * price)

    def test_it_is_never_more_than_the_ten_points_it_was(self):
        fixed_income, price = ECONOMIES["huge"]
        self.assertGreater(FLOOR_INCOME_SHARE * fixed_income / price, FLOOR_MAX_POINTS)
        self.assertEqual(Country(fixed_income, -1.0, price, reserves=0.5).script(), FLOOR_MAX_POINTS)
        self.assertEqual(before(Country(fixed_income, -1.0, price, reserves=0.5)), FLOOR_MAX_POINTS)

    def test_income_that_is_not_fixed_does_not_count(self):
        # The investment pool's repayment of private construction is income, and not the government's to spend.
        self.assertEqual(Country(2649.0, 0.0, 1143.0, reserves=0.3, income=2848.0).script(),
                         Country(2649.0, 0.0, 1143.0, reserves=0.3, income=99999.0).script())

    def test_it_shrinks_as_the_reserves_do(self):
        fixed_income, price = ECONOMIES["mid"]
        full = Country(fixed_income, 0.0, price, reserves=0.1).script_floor()
        self.assertAlmostEqual(full, FLOOR_INCOME_SHARE * fixed_income / price, delta=STEP)
        self.assertAlmostEqual(Country(fixed_income, 0.0, price, reserves=0.9).script_floor(), full, delta=STEP)
        self.assertAlmostEqual(Country(fixed_income, 0.0, price, reserves=0.05).script_floor(), full / 2, delta=STEP)
        self.assertAlmostEqual(Country(fixed_income, 0.0, price, reserves=0.02).script_floor(), full / 5, delta=STEP)

    def test_with_none_left_a_tenth_of_it_is_all_that_goes_on_credit(self):
        for name in ("tiny", "mid", "large", "huge"):
            fixed_income, price = ECONOMIES[name]
            for share, debt in itertools.product((-0.25, 0.0), (0.0, 0.05, 0.2, 0.39, 1.2)):
                c = Country(fixed_income, share * fixed_income, price, debt=debt)
                with self.subTest(economy=name, surplus=share, debt=debt):
                    self.assertLessEqual(c.bill(), 0.005 * fixed_income + STEP * price)
                    self.assertLessEqual(c.script(), 1.0 + STEP)

    def test_a_queued_level_always_gets_something(self):
        # With no base construction in a market game, a purchase of nothing leaves the queue where it stands.
        for fixed_income, price in ((300.0, 1999.0), (857.0, 1249.0), (13678.0, 1265.0)):
            for share, debt in itertools.product((-2.0, -0.2, 0.0, 0.001), (0.0, 0.1, 0.39, 0.99)):
                c = Country(fixed_income, share * fixed_income, price, debt=debt)
                with self.subTest(fixed_income=fixed_income, surplus=share, debt=debt):
                    self.assertGreater(c.script(), 0.0005)

    def test_short_of_bureaucracy_it_adds_a_fifth_of_fixed_income_at_the_price_in_play(self):
        for name in ("tiny", "mid", "large"):
            fixed_income, price = ECONOMIES[name]
            for debt in (0.0, 0.3):
                short = Country(fixed_income, 0.0, price, debt=debt, bureaucracy=-1.0, queued=50, weekly_max=140.0)
                enough = Country(fixed_income, 0.0, price, debt=debt, bureaucracy=0.0, queued=50, weekly_max=140.0)
                with self.subTest(economy=name, debt=debt):
                    self.assertAlmostEqual((short.script() - enough.script()) * price,
                                           BUREAUCRACY_INCOME_SHARE * fixed_income, delta=STEP * price)
                    # Before: a fifth of income at a price of 150, more than the country's whole income.
                    self.assertGreater((before(short) - before(enough)) * price, fixed_income)
                    self.assertLess(short.bill(), 0.21 * fixed_income)

    def test_the_old_price_clamp_is_gone(self):
        code = _code(AI_VALUES.read_text(encoding="utf-8-sig"))
        floor = code[code.index("te_construction_market_ai_purchase_floor = {"):
                     code.index("te_construction_market_ai_purchase_target = {")]
        self.assertNotRegex(floor, r"\bmax\s*=\s*150\b")
        self.assertNotRegex(floor, r"\bvalue\s*=\s*income\b")
        self.assertNotIn("te_construction_market_price\n", floor)
        self.assertEqual(floor.count("var:te_construction_market_price_stabilizer"), 2)


# February 1836, the second run of the AI telemetry probe on main 3a0e13409: tag, weekly income, fixed income, net
# fixed income, smoothed price, reserves and debt as shares of their limits, and the purchase logged.
SAMPLE = (
    ("KUN", 857, 857, 143, 1249, 0.0, 0.322, 10),
    ("SEL", 909, 909, 295, 1249, 0.0, 0.322, 10),
    ("KUT", 1318, 1318, 415, 1294, 0.0, 0.082, 10),
    ("SHS", 2848, 2649, 1813, 1143, 0.0, 0.029, 10),
    ("KON", 3189, 2989, 2357, 1249, 0.0, 0.086, 10),
    ("ASH", 3983, 3783, 781, 1298, 0.0, 0.071, 10),
    ("NSW", 1935, 1735, 809, 1294, 0.0, 0.032, 10),
    ("BAV", 13678, 13678, 2793, 1265, 0.16, 0.0, 10),
    ("TUR", 51870, 49749, 9176, 1406, 0.243, 0.0, 10),
)


class TheEvidence(unittest.TestCase):
    def countries(self):
        for tag, income, fixed_income, surplus, price, reserves, debt, logged in SAMPLE:
            yield tag, logged, Country(fixed_income, surplus, price, reserves, debt, income=income)

    def test_the_rule_before_gives_what_the_probe_logged(self):
        for tag, logged, c in self.countries():
            with self.subTest(tag=tag):
                self.assertEqual(before(c), logged)

    def test_the_floor_cost_most_of_them_more_than_their_income(self):
        over = [tag for tag, logged, c in self.countries() if logged * c.price > c.income]
        self.assertEqual(over, ["KUN", "SEL", "KUT", "SHS", "KON", "ASH", "NSW"])

    def test_now_each_spends_no_more_than_it_has(self):
        # Its surplus, raised by its reserves and lowered by its debt: never a loan.
        for tag, _, c in self.countries():
            with self.subTest(tag=tag):
                self.assertAlmostEqual(c.bill(), c.surplus * (1 + c.reserves - c.debt), delta=STEP * c.price)
                self.assertLess(c.bill(), 0.75 * c.income)
                self.assertGreater(c.script(), 0.0)


# ---------------------------------------------------------------------------
# The long run: a week-by-week budget, the same for both rules.
# ---------------------------------------------------------------------------
# Income, the other fixed bills and the price are constant and a level is always queued. Interest is a fixed expense,
# so the surplus falls as debt rises. A surplus pays debt, then fills the reserves; a deficit empties the reserves,
# then borrows. The engine pauses construction at 40% of the debt ceiling and resumes at 20%. The ceiling is 250 weeks
# of income and the reserve limit 17 (the 1836 probe's two runs: medians of 235 and 253, and of 15 and 18); interest
# is 10% a year, between the save study's medians for AI countries with no bankruptcy premium (8.6% and 11.0%). A
# country whose debt passes its ceiling is in default; the model lets the debt run on and notes the year.
CEILING_WEEKS, RESERVE_WEEKS, RATE = 250.0, 17.0, 0.10


class Run:
    def __init__(self, by_year, debt, paused_weeks, default_year):
        self.by_year, self.debt, self.paused_weeks, self.default_year = by_year, debt, paused_weeks, default_year


def long_run(rule, fixed_income, surplus_share, years, price=1250.0):
    """Points bought by the end of each year, the debt share at the end, the weeks paused, the year of default."""
    ceiling, limit = CEILING_WEEKS * fixed_income, RESERVE_WEEKS * fixed_income
    gold = debt = points = 0.0
    paused, paused_weeks, by_year, default_year = False, 0, [], None
    for week in range(1, years * 52 + 1):
        surplus = surplus_share * fixed_income - RATE * debt / 52
        share = debt / ceiling
        if paused and share <= NAI["CONSTRUCTION_DEBT_RESUME"]:
            paused = False
        elif not paused and share >= NAI["CONSTRUCTION_DEBT_PAUSE"]:
            paused = True
        paused_weeks += paused
        bought = rule(Country(fixed_income, surplus, price, gold / limit, share, paused=paused))
        points += bought
        balance = surplus - bought * price
        if balance >= 0:
            repaid = min(balance, debt)
            debt -= repaid
            gold = min(limit, gold + balance - repaid)
        else:
            drawn = min(gold, -balance)
            gold -= drawn
            debt += -balance - drawn
        if default_year is None and debt >= ceiling:
            default_year = math.ceil(week / 52)
        if week % 52 == 0:
            by_year.append(points)
    return Run(by_year, debt / ceiling, paused_weeks, default_year)


def now(c):
    return c.script()


class TheLongRun(unittest.TestCase):
    """A small country (3,000 a week; a 100-point level costs 42 weeks of its whole income) under both rules."""

    def test_the_rule_before_borrowed_to_the_pause_within_a_year(self):
        for share in (0.0, 0.1, 0.33, 0.7):
            run = long_run(before, 3000.0, share, 30)
            with self.subTest(surplus=share):
                # 40% of the ceiling is 100 weeks of income, and ten points a week cost four weeks of it.
                self.assertGreaterEqual(run.paused_weeks, 0.8 * 30 * 52)

    def test_a_surplus_under_a_fifth_of_income_never_left_the_pause_and_ended_in_default(self):
        # Interest on 40% of the ceiling is 250 x 0.4 x 10% / 52 = 19% of income.
        for share in (0.0, 0.06, 0.1, 0.17):
            run = long_run(before, 3000.0, share, 30)
            with self.subTest(surplus=share):
                self.assertEqual(run.by_year[0], run.by_year[-1])
                self.assertIsNotNone(run.default_year)
                self.assertLessEqual(run.default_year, 30)

    def test_now_a_country_with_a_surplus_never_borrows_and_never_pauses(self):
        for share in (0.006, 0.06, 0.17, 0.33, 0.7):
            run = long_run(now, 3000.0, share, 30)
            with self.subTest(surplus=share):
                self.assertLess(run.debt, 1e-6)
                self.assertEqual(run.paused_weeks, 0)
                self.assertIsNone(run.default_year)
                # The surplus, every year.
                self.assertAlmostEqual(run.by_year[-1] / 30, share * 3000.0 * 52 / 1250.0, delta=0.05)

    def test_over_thirty_years_it_builds_more_than_the_rule_before(self):
        for share in (0.1, 0.17, 0.33, 0.5, 0.7):
            with self.subTest(surplus=share):
                self.assertGreater(long_run(now, 3000.0, share, 30).by_year[-1],
                                   long_run(before, 3000.0, share, 30).by_year[-1])

    def test_the_rule_before_is_ahead_at_first_by_no_more_than_it_borrowed(self):
        # The old burst is 40% of the ceiling, 100 weeks of the country's income, on credit. The steady rule passes
        # it once it has spent as much from its surplus, sooner where the old one goes on paying interest.
        for share, by in ((0.1, 21), (0.17, 12), (0.33, 10), (0.7, 10)):
            old, new = long_run(before, 3000.0, share, 30).by_year, long_run(now, 3000.0, share, 30).by_year
            passed = next(year for year in range(1, 31) if new[year - 1] >= old[year - 1])
            with self.subTest(surplus=share):
                self.assertGreater(old[0], new[0])
                self.assertLessEqual(max(o - n for o, n in zip(old, new)), 0.4 * CEILING_WEEKS * 3000.0 / 1250.0)
                self.assertLessEqual(passed, by)

    def test_the_class_that_builds_less_is_the_one_that_built_by_defaulting(self):
        # A surplus of 6% of income: the old burst is still ahead after thirty years, because 100 weeks of income is
        # 32 years of such a surplus. The old country spent 29 of them paused and was in default by the twelfth year;
        # the new one owes nothing.
        old, new = long_run(before, 3000.0, 0.06, 30), long_run(now, 3000.0, 0.06, 30)
        self.assertGreater(old.by_year[-1], new.by_year[-1])
        self.assertLessEqual(old.default_year, 12)
        self.assertGreater(new.by_year[-1], 0.9 * old.by_year[-1])
        self.assertLess(new.debt, 1e-6)

    def test_with_no_surplus_at_all_the_part_on_credit_takes_decades_to_matter(self):
        # A two-hundredth of income a week, borrowed, with interest on it: under 2% of the ceiling after ten years
        # and a fifth after thirty, never paused. The rule before was past the ceiling inside ten.
        self.assertLess(long_run(now, 3000.0, 0.0, 10).debt, 0.02)
        thirty = long_run(now, 3000.0, 0.0, 30)
        self.assertLess(thirty.debt, 0.25)
        self.assertEqual(thirty.paused_weeks, 0)
        self.assertLessEqual(long_run(before, 3000.0, 0.0, 30).default_year, 10)


class Wiring(unittest.TestCase):
    def test_only_an_ai_country_in_a_market_game_runs_it(self):
        pulse = PULSE.read_text(encoding="utf-8-sig")
        direct = pulse.index("te_direct_construction_on_weekly_pulse = yes")
        market = pulse.index("else_if = {", direct)
        call = pulse.index("te_construction_market_ai_update_buy = yes")
        self.assertLess(market, call)
        self.assertRegex(pulse[market:call], r"if = \{\s*limit = \{\s*is_ai = yes\s*\}\s*$")
        callers = [p.name for p in sorted((ROOT / "common").rglob("*.txt"))
                   if "te_construction_market_ai_update_buy = yes" in p.read_text(encoding="utf-8-sig")]
        self.assertEqual(callers, [PULSE.name])

    def test_it_writes_the_purchase_and_nothing_else(self):
        effect = _code(AI_EFFECTS.read_text(encoding="utf-8-sig"))
        self.assertRegex(effect, r"name = te_construction_market_public_target\s+"
                                 r"value = te_construction_market_ai_purchase_target")
        self.assertEqual(re.findall(r"\b(?:set_variable|add_modifier|change_variable)\b", effect), ["set_variable"])

    def test_the_docs_and_the_play_test_list_carry_it(self):
        self.assertIn("**The AI's purchase.**", SYSTEM_DOC.read_text(encoding="utf-8"))
        self.assertIn("## AI Government Construction", AI_DOC.read_text(encoding="utf-8"))
        playtest = PLAYTEST.read_text(encoding="utf-8")
        self.assertIn("## The AI's construction purchase fits its budget", playtest)
        for field in ("cm_public", "cm_price", "debt_scaled", "paused"):
            self.assertIn(f"`{field}`", playtest)

    def test_the_play_test_rows_name_fields_the_probe_logs(self):
        # The AI telemetry probe is temporary (docs/testing/ai-probe-runbook.md): once it is removed there is nothing
        # to hold the rows to.
        if not PROBE_KEY.is_file():
            self.skipTest("the AI telemetry probe is not in this build")
        key = json.loads(PROBE_KEY.read_text(encoding="utf-8"))
        logged = {name for names in key["lines"].values() for name in names}
        logged |= {f"n_{name}" for name in key["counters"]} | set(key["data_functions"])
        playtest = PLAYTEST.read_text(encoding="utf-8")
        section = playtest[playtest.index("## The AI's construction purchase fits its budget"):]
        section = section[:section.index("\n## ", 5)] if "\n## " in section[5:] else section
        named = set(re.findall(r"`([a-z][a-z_0-9]*)`", section))
        fields = {name for name in named if not name.startswith("te_") and name not in ("main", "is_ai")}
        self.assertGreaterEqual(len(fields), 20)
        self.assertEqual(sorted(fields - logged), [])


def _code(text):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in text.splitlines())


def _game_file(name):
    try:
        from path_constants import base_game_path
    except Exception:
        return None
    path = Path(base_game_path) / "game/common" / name
    return path if path.is_file() else None


if __name__ == "__main__":
    unittest.main()
