"""What an AI government buys a week in a market game (te_construction_market_ai_purchase_target).

common/script_values/te_construction_market_ai_values.txt sets the purchase: the country's budget surplus over the
smoothed price, scaled by reserves and debt, or a floor if that is more, capped by the government queue. Until
2026-11-15 the floor was 10 points a week for every country, which was more than the whole weekly income of 23 of the
28 AI countries buying in February 1836; they borrowed to the engine's construction pause within months. The floor is
now a twentieth of fixed income, never more than the 10 points it was, paid from reserves (nothing with none) or,
up to a tenth of it, from the surplus, and a fifth of fixed income higher while the country is short of bureaucracy,
so such a country buys at least a fifth. A government with no surplus, no reserves and no such shortage buys nothing.
While the engine reports construction paused the purchase is nothing, whatever the country's bureaucracy. For a day
(2026-11-16) a paused country short of bureaucracy with a Government Administration level in its queue went on buying
that fifth; an observer game showed that nothing bought while paused reaches the government queue, so that clause and
its self-check were removed (docs/systems/mod_systems/construction.md, "The AI's purchase").

Nothing in the engine checks that script, so this runs the script's own text. What each part checks:

- ScriptAgainstModel runs the values through the evaluator of test_construction_market_budget_step.py, with the
  engine's reads (income, debt, reserves, the queue) stubbed, against the same rule restated in Python
  (`model`). The restatement follows the script line by line, so it checks the script's operators and their order,
  and that a value does what its comment says; it would repeat a mistake in the rule itself.
- Surplus, Floor, ShortOfBureaucracy, Paused, TheSites, TheEvidence and TheLongRun are the independent checks:
  properties the rule must have whatever its wording (what it costs against income, that it never rises above the
  rule before, that a paused country buys nothing, that the probe's sample countries spend no more than they have),
  and a week-by-week budget against the rule before.
- Constants holds the script's constants to the engine defines they are taken from.

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

# The rule, restated here.
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
    "CONSTRUCTION_DEBT_PAUSE_CRITICAL_CONSTRUCTION": 0.99,
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
    return _PARSED


class AiEnv(Env):
    """The shared evaluator with the AI values file loaded too, and the files parsed once."""

    def __init__(self, names, variables, flags):
        parsed = _parsed()
        self.memo = {}
        self.constants, self.values = parsed["constants"], parsed["values"]
        self.names, self.variables, self.flags = names, variables, flags
        # te_construction_market_triggers.txt: a Fixed Budget is on while this variable is set.
        budget_mode = "te_construction_market_budget_mode"
        self.triggers = {budget_mode + "_on": lambda: budget_mode in variables}

    def operand(self, raw):
        # The engine's numbers have five decimals; the shared evaluator's floats carry noise past that, which a
        # comparison with 0 would read as a quantity.
        return round(super().operand(raw), 5)


class Country:
    """One week of one government, as the script reads it."""

    def __init__(self, fixed_income, surplus, price=1250.0, reserves=0.0, debt=0.0, bureaucracy=50.0, queued=1,
                 weekly_max=20.0, paused=False, at_war=False, bubble=None, income=None):
        self.fixed_income = float(fixed_income)
        self.surplus = float(surplus)  # net_fixed_income
        self.price = float(price)  # var:te_construction_market_price_stabilizer
        self.reserves, self.debt = reserves, debt  # scaled_gold_reserves, scaled_debt
        self.bureaucracy, self.queued, self.weekly_max = bureaucracy, queued, weekly_max
        self.paused, self.at_war, self.bubble = paused, at_war, bubble
        self.income = float(fixed_income if income is None else income)  # read by the rule before only
        self.vars = {"te_construction_market_price_stabilizer": self.price}
        if bubble is not None:
            self.vars["bubble_pressure"] = bubble

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
        # The evaluator fails on a read it has no stub for. There is none for is_ai, for a building or for income
        # that is not fixed: the purchase and the sites' use of it may read none of them.
        return AiEnv(names, self.vars, flags={"is_construction_paused": self.paused, "is_at_war": self.at_war})

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
    whole = min(FLOOR_MAX_POINTS, FLOOR_INCOME_SHARE * c.fixed_income / c.price)
    from_reserves = whole * max(0.0, min(1.0, c.reserves / FLOOR_FULL_RESERVES))
    from_surplus = min(max(c.surplus, 0.0) / c.price, whole * FLOOR_MIN_FACTOR)
    floor = max(from_reserves, from_surplus)
    if c.bureaucracy < 0:
        floor += BUREAUCRACY_INCOME_SHARE * c.fixed_income / c.price
    return floor


def model(c):
    """The script's rule restated line by line (see the module's docstring for what that does and does not check)."""
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
        constants = _parsed()["constants"]
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

    def test_the_part_the_surplus_pays_is_a_two_hundredth_of_income(self):
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

    def test_paused_and_not(self):
        count = 0
        budgets = ((0.0, 0.0), (0.3, 0.0), (0.0, 0.45), (0.0, 0.9))  # reserves, debt
        for (name, (fixed_income, price)), share, (reserves, debt), bureaucracy, paused, (queued, cap) in \
                itertools.product(ECONOMIES.items(), (-0.25, 0.03, 0.33), budgets, (50.0, -5.0), (False, True),
                                  ((0, 20.0), (1, 10.0), (3, 20.0), (1, 140.0))):
            c = Country(fixed_income, share * fixed_income, price, reserves, debt, bureaucracy, queued, cap,
                        paused=paused)
            count += 1
            with self.subTest(economy=name, surplus=share, reserves=reserves, debt=debt, bureaucracy=bureaucracy,
                              paused=paused, queue=(queued, cap)):
                self.assertAlmostEqual(c.script(), model(c), delta=STEP)
        self.assertGreater(count, 350)

    def test_it_is_not_rounded_to_whole_points(self):
        # A surplus of 143 a week (Kunduz's) buys a ninth of a point with no debt. Whole points made that nothing.
        self.assertAlmostEqual(Country(857.0, 143.0, 1249.0).script(), 143.0 / 1249.0, delta=STEP)
        self.assertNotIn("round", _code(AI_VALUES.read_text(encoding="utf-8-sig")))

    def test_with_an_empty_queue_it_buys_nothing(self):
        for paused, bureaucracy in itertools.product((False, True), (50.0, -50.0)):
            with self.subTest(paused=paused, bureaucracy=bureaucracy):
                c = Country(75817.0, 30000.0, bureaucracy=bureaucracy, paused=paused, queued=0)
                self.assertEqual(c.script(), 0.0)

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
        # At any price over 150, where the old bureaucracy clause's clamp stopped holding its price down, and
        # outside the engine's pause, where the rule before bought nothing.
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

    def test_it_shrinks_as_the_reserves_do_to_nothing(self):
        fixed_income, price = ECONOMIES["mid"]
        full = Country(fixed_income, 0.0, price, reserves=0.1).script_floor()
        self.assertAlmostEqual(full, FLOOR_INCOME_SHARE * fixed_income / price, delta=STEP)
        self.assertAlmostEqual(Country(fixed_income, 0.0, price, reserves=0.9).script_floor(), full, delta=STEP)
        self.assertAlmostEqual(Country(fixed_income, 0.0, price, reserves=0.05).script_floor(), full / 2, delta=STEP)
        self.assertAlmostEqual(Country(fixed_income, 0.0, price, reserves=0.02).script_floor(), full / 5, delta=STEP)
        self.assertAlmostEqual(Country(fixed_income, 0.0, price, reserves=0.002).script_floor(), full / 50, delta=STEP)
        self.assertEqual(Country(fixed_income, 0.0, price, reserves=0.0).script_floor(), 0.0)

    def test_no_surplus_and_no_reserves_buys_nothing(self):
        # Owner, 2026-11-16: a government that cannot cover its fixed bills and has nothing put by buys nothing. No
        # part of the floor is on credit. Its queued level waits: a market game has no base construction.
        for name in ECONOMIES:
            fixed_income, price = ECONOMIES[name]
            for share, debt in itertools.product((-2.0, -0.25, 0.0), (0.0, 0.05, 0.2, 0.39)):
                c = Country(fixed_income, share * fixed_income, price, debt=debt)
                with self.subTest(economy=name, surplus=share, debt=debt):
                    self.assertEqual(c.script(), 0.0)

    def test_no_surplus_with_reserves_buys_what_the_reserves_carry(self):
        for name in ("tiny", "mid", "large"):
            fixed_income, price = ECONOMIES[name]
            for share, reserves in itertools.product((-0.25, 0.0), (0.004, 0.03, 0.1, 0.6)):
                c = Country(fixed_income, share * fixed_income, price, reserves=reserves)
                with self.subTest(economy=name, surplus=share, reserves=reserves):
                    self.assertAlmostEqual(c.bill(), FLOOR_INCOME_SHARE * fixed_income * min(1.0, reserves / 0.1),
                                           delta=STEP * price)

    def test_a_small_surplus_with_no_reserves_buys_the_surplus(self):
        # No reserves and no debt: the surplus term spends the surplus exactly, and the floor never asks for more
        # than the surplus, however small. Before, a surplus under a 200th of income bought the 200th on credit.
        for name in ECONOMIES:
            fixed_income, price = ECONOMIES[name]
            for share in (0.0001, 0.001, 0.004, 0.005, 0.02, 0.17):
                c = Country(fixed_income, share * fixed_income, price, queued=50, weekly_max=140.0)
                with self.subTest(economy=name, surplus=share):
                    self.assertAlmostEqual(c.bill(), c.surplus, delta=STEP * price)

    def test_no_part_of_the_floor_is_ever_on_credit(self):
        # Whatever the surplus, the debt and the brakes: with no reserves and no shortage of bureaucracy, the bill is
        # never more than the surplus.
        for (fixed_income, price), share, debt, at_war, bubble in itertools.product(
                ECONOMIES.values(), (-0.3, 0.0, 0.0005, 0.003, 0.01, 0.2), (0.0, 0.1, 0.39), (False, True),
                (None, 80.0)):
            c = Country(fixed_income, share * fixed_income, price, debt=debt, at_war=at_war, bubble=bubble)
            with self.subTest(fixed_income=fixed_income, surplus=share, debt=debt, at_war=at_war, bubble=bubble):
                self.assertLessEqual(c.bill(), max(c.surplus, 0.0) + STEP * price)

    def test_with_a_surplus_and_no_reserves_a_tenth_of_it_holds_against_debt_and_the_brakes(self):
        # At exactly no reserves the floor is the smaller of a tenth of the twentieth and the surplus itself. It
        # binds only where debt or the brakes cut the surplus term under it, and the surplus pays for it.
        fixed_income, price = ECONOMIES["mid"]
        tenth = FLOOR_MIN_FACTOR * FLOOR_INCOME_SHARE * fixed_income / price
        at_war = Country(fixed_income, 0.02 * fixed_income, price, debt=0.3, at_war=True)  # the factor is 0.2
        self.assertLess(0.02 * fixed_income / price * 0.2, tenth)
        self.assertAlmostEqual(at_war.script(), tenth, delta=STEP)
        self.assertLess(at_war.bill(), at_war.surplus)
        thin = Country(fixed_income, 0.003 * fixed_income, price, debt=0.3, at_war=True)
        self.assertAlmostEqual(thin.script(), 0.003 * fixed_income / price, delta=STEP)
        calm = Country(fixed_income, 0.02 * fixed_income, price)
        self.assertAlmostEqual(calm.script(), 0.02 * fixed_income / price, delta=STEP)

    def test_the_war_and_banking_brakes_do_not_touch_what_reserves_pay(self):
        fixed_income, price = ECONOMIES["mid"]
        for reserves in (0.0, 0.05, 0.2):
            calm = Country(fixed_income, 0.0, price, reserves=reserves)
            shaken = Country(fixed_income, 0.0, price, reserves=reserves, at_war=True, bubble=80.0)
            with self.subTest(reserves=reserves):
                self.assertEqual(shaken.script(), calm.script())

    def test_the_old_price_clamp_is_gone(self):
        code = _code(AI_VALUES.read_text(encoding="utf-8-sig"))
        floor = code[code.index("te_construction_market_ai_bureaucracy_purchase = {"):
                     code.index("te_construction_market_ai_purchase_target = {")]
        self.assertNotRegex(floor, r"\bmax\s*=\s*150\b")
        self.assertNotRegex(floor, r"\bvalue\s*=\s*income\b")
        self.assertNotIn("te_construction_market_price\n", floor)
        # Every division is by the smoothed price: the fifth, the twentieth, and the surplus that pays the tenth.
        self.assertEqual(floor.count("var:te_construction_market_price_stabilizer"), 3)
        self.assertEqual(floor.count("divide ="), 4)  # those three, and reserves over the tenth of their limit


class ShortOfBureaucracy(unittest.TestCase):
    """The clause is a floor: at least a fifth of fixed income, not a fifth on top of what the surplus buys."""

    def test_with_no_surplus_it_buys_a_fifth_of_fixed_income_at_the_price_in_play(self):
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

    def test_it_is_never_less_than_a_fifth_outside_the_pause(self):
        for (fixed_income, price), share, (reserves, debt) in itertools.product(
                ECONOMIES.values(), (-0.25, 0.0, 0.1, 0.33, 0.7), ((0.0, 0.0), (0.4, 0.0), (0.0, 0.39))):
            c = Country(fixed_income, share * fixed_income, price, reserves, debt, bureaucracy=-1.0, queued=50,
                        weekly_max=100000.0)
            with self.subTest(fixed_income=fixed_income, surplus=share, reserves=reserves, debt=debt):
                self.assertGreaterEqual(c.bill(), BUREAUCRACY_INCOME_SHARE * fixed_income - STEP * price)

    def test_where_the_surplus_buys_more_the_shortage_adds_nothing(self):
        # Sokoto, February 1836: 4 short on a fixed income of 11,806 and a surplus of 6,174. The surplus term buys
        # 4.49 points; the floor with the clause is 0.04 + 1.72.
        short = Country(11806.0, 6174.0, 1369.0, debt=0.004, bureaucracy=-4.0, queued=50, weekly_max=140.0,
                        income=12261.0)
        enough = Country(11806.0, 6174.0, 1369.0, debt=0.004, bureaucracy=4.0, queued=50, weekly_max=140.0,
                         income=12261.0)
        self.assertAlmostEqual(short.script(), 6174.0 / 1369.0 * 0.996, delta=STEP)
        self.assertEqual(short.script(), enough.script())
        # Its floor still has the tenth, which its surplus pays.
        self.assertAlmostEqual(short.script_floor(), 0.1 * 0.05 * 11806.0 / 1369.0 + 0.2 * 11806.0 / 1369.0, delta=STEP)
        self.assertEqual(before(short), 26.0)


class Paused(unittest.TestCase):
    """While the engine reports construction paused an AI buys nothing, whatever its bureaucracy. A purchase through
    the pause for a queued Government Administration was tried on 2026-11-16 and removed the same day: an observer
    game showed that nothing bought while paused reaches the government queue (construction.md, "The AI's
    purchase")."""

    def test_it_buys_nothing_whatever_its_bureaucracy(self):
        count = 0
        for (name, (fixed_income, price)), share, (reserves, debt), bureaucracy, (queued, cap) in itertools.product(
                ECONOMIES.items(), (-0.3, 0.0, 0.03, 0.5), ((0.0, 0.41), (0.0, 0.7), (0.0, 0.98), (0.3, 0.0)),
                (-763.0, -5.0, 0.0, 50.0), ((1, 20.0), (14, 30.0), (50, 140.0))):
            c = Country(fixed_income, share * fixed_income, price, reserves, debt, bureaucracy, queued, cap,
                        paused=True)
            count += 1
            with self.subTest(economy=name, surplus=share, reserves=reserves, debt=debt, bureaucracy=bureaucracy,
                              queue=(queued, cap)):
                self.assertEqual(c.script(), 0.0)
        self.assertGreater(count, 700)

    def test_the_script_reads_nothing_of_a_paused_country_but_the_pause(self):
        # The evaluator fails on a read it has no stub for, and here it has the pause alone: no income, no debt, no
        # bureaucracy, no queue, no buildings, and not whether the AI or a player runs the country.
        env = AiEnv({}, {}, flags={"is_construction_paused": True})
        self.assertEqual(env.value("te_construction_market_ai_purchase_target"), 0.0)

    def test_the_same_shortage_still_buys_its_fifth_where_the_engine_reports_no_pause(self):
        # The floor's fifth does not shrink with debt (the owner's point of 2026-11-16, that a shortage of
        # bureaucracy limits income), and the engine does not always report the pause at 40% of the ceiling.
        for name in ("tiny", "mid", "large"):
            fixed_income, price = ECONOMIES[name]
            for surplus, debt in itertools.product((-0.3, 0.0), (0.41, 0.7, 0.98)):
                c = Country(fixed_income, surplus * fixed_income, price, debt=debt, bureaucracy=-5.0, queued=50,
                            weekly_max=140.0, paused=True)
                with self.subTest(economy=name, surplus=surplus, debt=debt):
                    self.assertEqual(c.script(), 0.0)
                    c.paused = False
                    self.assertAlmostEqual(c.bill(), BUREAUCRACY_INCOME_SHARE * fixed_income, delta=STEP * price)

    def test_east_india_in_1877(self):
        # The observer game of 2026-11-16 on main 81b947368: paused at 47% of its debt ceiling, 763 short of
        # bureaucracy, 14 government levels queued at 30 points a week each. The clause bought it 30 points a week,
        # and its government queue used none of them (TE_SELF_CHECK BROKEN construction_admin_while_paused, after 14
        # weeks and 420 points).
        east_india = Country(434223.0, -69194.0, 1242.0, debt=0.472, bureaucracy=-763.0, queued=14, weekly_max=30.0,
                             paused=True, income=596386.0)
        self.assertEqual(east_india.script(), 0.0)
        # Had the engine reported no pause, the floor's fifth: 69.9 points.
        east_india.paused = False
        self.assertAlmostEqual(east_india.script(), 0.2 * 434223.0 / 1242.0, delta=STEP)


class TheSites(unittest.TestCase):
    """te_construction_market_public_use_target, which sizes the Construction Sites, is nothing whenever the engine
    reports the pause, for the AI and for a player."""

    def use(self, purchase=6.0, **kwargs):
        c = Country(13678.0, 0.0, 1265.0, **kwargs)
        c.vars["te_construction_market_public_target"] = purchase
        return c.env().value("te_construction_market_public_use_target")

    def test_paused_it_is_nothing_whatever_the_purchase_and_the_bureaucracy(self):
        for purchase, bureaucracy in itertools.product((0.5, 6.0, 90.0), (-763.0, -5.0, 5.0)):
            with self.subTest(purchase=purchase, bureaucracy=bureaucracy):
                self.assertEqual(self.use(purchase, paused=True, bureaucracy=bureaucracy, queued=14, weekly_max=30.0),
                                 0.0)

    def test_it_reads_nothing_of_a_paused_country_but_the_pause(self):
        # As for the purchase: with the pause and the purchase variable alone, nothing else is read. So it cannot
        # tell an AI's country from a player's, or one short of bureaucracy from another.
        env = AiEnv({}, {"te_construction_market_public_target": 30.0}, flags={"is_construction_paused": True})
        self.assertEqual(env.value("te_construction_market_public_use_target"), 0.0)

    def test_unpaused_it_is_the_purchase_up_to_the_queues_cap(self):
        for bureaucracy in (-5.0, 5.0):
            with self.subTest(bureaucracy=bureaucracy):
                self.assertEqual(self.use(bureaucracy=bureaucracy), 6.0)
                self.assertEqual(self.use(purchase=90.0, bureaucracy=bureaucracy), 20.0)


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
#
# Both rules size the purchase on the smoothed price, 1,250. What the rule before paid for its points was the price
# ceiling: its floors asked for several times what the markets made, and the probe's rows show 10 x 1,999 billed
# (docs/systems/mod_systems/construction.md). `paid` is that price; without it the old burst is priced as if the
# market had not noticed it.
CEILING_WEEKS, RESERVE_WEEKS, RATE = 250.0, 17.0, 0.10
PRICE, PRICE_PAID_BEFORE = 1250.0, 1999.0


class Run:
    def __init__(self, by_year, debt, paused_weeks, default_year):
        self.by_year, self.debt, self.paused_weeks, self.default_year = by_year, debt, paused_weeks, default_year


def long_run(rule, fixed_income, surplus_share, years, price=PRICE, paid=None, tax_raise=0.0):
    """Points bought by the end of each year, the debt share at the end, the weeks paused, the year of default.
    `tax_raise` is what the engine's budget AI might add to income, as a share of it, once debt is over a tenth of
    the ceiling (NAI CHANGE_TAX_SIGNIFICANT_DEBT_THRESHOLD)."""
    ceiling, limit = CEILING_WEEKS * fixed_income, RESERVE_WEEKS * fixed_income
    gold = debt = points = 0.0
    paused, paused_weeks, by_year, default_year = False, 0, [], None
    for week in range(1, years * 52 + 1):
        share = debt / ceiling
        surplus = surplus_share * fixed_income - RATE * debt / 52 + (tax_raise * fixed_income if share > 0.1 else 0.0)
        if paused and share <= NAI["CONSTRUCTION_DEBT_RESUME"]:
            paused = False
        elif not paused and share >= NAI["CONSTRUCTION_DEBT_PAUSE"]:
            paused = True
        paused_weeks += paused
        bought = rule(Country(fixed_income, surplus, price, gold / limit, share, paused=paused))
        points += bought
        balance = surplus - bought * (paid or price)
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
        for share, paid in itertools.product((0.0, 0.1, 0.33, 0.7), (None, PRICE_PAID_BEFORE)):
            run = long_run(before, 3000.0, share, 30, paid=paid)
            with self.subTest(surplus=share, paid=paid):
                # 40% of the ceiling is 100 weeks of income, and ten points a week cost four to seven weeks of it.
                self.assertGreaterEqual(run.paused_weeks, 0.8 * 30 * 52)

    def test_a_surplus_under_a_fifth_of_income_never_left_the_pause_and_ended_in_default(self):
        # Interest on 40% of the ceiling is 250 x 0.4 x 10% / 52 = 19% of income.
        for share, paid in itertools.product((0.0, 0.06, 0.1, 0.17), (None, PRICE_PAID_BEFORE)):
            run = long_run(before, 3000.0, share, 30, paid=paid)
            with self.subTest(surplus=share, paid=paid):
                self.assertEqual(run.by_year[0], run.by_year[-1])
                self.assertIsNotNone(run.default_year)
                self.assertLessEqual(run.default_year, 30)

    def test_now_a_country_with_a_surplus_never_borrows_and_never_pauses(self):
        for share in (0.0005, 0.006, 0.06, 0.17, 0.33, 0.7):
            run = long_run(now, 3000.0, share, 30)
            with self.subTest(surplus=share):
                self.assertLess(run.debt, 1e-6)
                self.assertEqual(run.paused_weeks, 0)
                self.assertIsNone(run.default_year)
                # The surplus, every year.
                self.assertAlmostEqual(run.by_year[-1] / 30, share * 3000.0 * 52 / PRICE, delta=0.05)

    def test_at_the_price_it_paid_the_old_burst_was_about_150_points(self):
        # 40% of the ceiling, 100 weeks of income, at 1,999 a point; 240 to 260 if it had paid the smoothed 1,250.
        for share in (0.0, 0.06, 0.17):
            with self.subTest(surplus=share):
                self.assertTrue(140 <= long_run(before, 3000.0, share, 30, paid=PRICE_PAID_BEFORE).by_year[0] <= 170)
                self.assertTrue(230 <= long_run(before, 3000.0, share, 30).by_year[0] <= 260)

    def test_over_thirty_years_it_builds_more_than_the_rule_before_at_every_surplus(self):
        # At the price the rule before paid, down to a surplus of 6% of income.
        for share in (0.06, 0.1, 0.17, 0.33, 0.5, 0.7):
            old = long_run(before, 3000.0, share, 30, paid=PRICE_PAID_BEFORE).by_year
            new = long_run(now, 3000.0, share, 30).by_year
            with self.subTest(surplus=share):
                self.assertGreater(new[-1], old[-1])
                self.assertLessEqual(next(year for year in range(1, 31) if new[year - 1] >= old[year - 1]), 21)

    def test_the_rule_before_is_ahead_at_first_by_no_more_than_it_borrowed(self):
        # Even priced at the smoothed price, as if the market had not noticed the burst: 40% of the ceiling, 100
        # weeks of the country's income, on credit. The steady rule passes it once it has spent as much from its
        # surplus, sooner where the old one goes on paying interest.
        for share, by in ((0.1, 21), (0.17, 12), (0.33, 10), (0.7, 10)):
            old, new = long_run(before, 3000.0, share, 30).by_year, long_run(now, 3000.0, share, 30).by_year
            passed = next(year for year in range(1, 31) if new[year - 1] >= old[year - 1])
            with self.subTest(surplus=share):
                self.assertGreater(old[0], new[0])
                self.assertLessEqual(max(o - n for o, n in zip(old, new)), 0.4 * CEILING_WEEKS * 3000.0 / PRICE)
                self.assertLessEqual(passed, by)

    def test_only_the_old_burst_at_the_smoothed_price_stays_ahead_at_a_thin_surplus(self):
        # A surplus of 6%: priced at 1,250 the old burst is 240 points, 32 years of that surplus, and still ahead at
        # thirty years. It paid 1,999, bought 150, and is passed in year 21. Either way it was in default by the
        # twelfth year and the new rule owes nothing.
        cheap = long_run(before, 3000.0, 0.06, 30)
        paid = long_run(before, 3000.0, 0.06, 30, paid=PRICE_PAID_BEFORE)
        new = long_run(now, 3000.0, 0.06, 30)
        self.assertGreater(cheap.by_year[-1], new.by_year[-1])
        self.assertLess(paid.by_year[-1], new.by_year[-1])
        self.assertLessEqual(max(cheap.default_year, paid.default_year), 12)
        self.assertLess(new.debt, 1e-6)

    def test_the_one_near_tie_is_a_thin_surplus_whose_taxes_rise_with_debt(self):
        # If the engine's AI adds 15% of income in taxes once debt passes a tenth of the ceiling, a 6% country under
        # the rule before leaves the pause now and then and reaches 240 points in thirty years, against 225.
        old = long_run(before, 3000.0, 0.06, 30, paid=PRICE_PAID_BEFORE, tax_raise=0.15)
        new = long_run(now, 3000.0, 0.06, 30)
        self.assertIsNone(old.default_year)
        self.assertAlmostEqual(old.by_year[-1] / new.by_year[-1], 1.0, delta=0.1)
        # From a surplus of 17% the new rule is ahead again even so.
        self.assertGreater(long_run(now, 3000.0, 0.17, 30).by_year[-1],
                           long_run(before, 3000.0, 0.17, 30, paid=PRICE_PAID_BEFORE, tax_raise=0.15).by_year[-1])

    def test_with_no_surplus_at_all_it_buys_nothing_and_owes_nothing(self):
        # Until 2026-11-16 a tenth of the floor went on credit here: about 19 points in thirty years (0.6 a year, a
        # 100-point level in 160 years) for a debt of a fifth of the ceiling, most of it interest. The rule before
        # was past the ceiling inside ten years.
        thirty = long_run(now, 3000.0, 0.0, 30)
        self.assertEqual(thirty.by_year[-1], 0.0)
        self.assertEqual(thirty.debt, 0.0)
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
        # ... and nothing else in that block.
        self.assertRegex(pulse[call:], r"^te_construction_market_ai_update_buy = yes\s+\}")
        callers = [p.name for p in sorted((ROOT / "common").rglob("*.txt"))
                   if "te_construction_market_ai_update_buy = yes" in p.read_text(encoding="utf-8-sig")]
        self.assertEqual(callers, [PULSE.name])

    def test_it_writes_the_purchase_and_nothing_else(self):
        effect = _code(AI_EFFECTS.read_text(encoding="utf-8-sig"))
        effect = effect[effect.index("te_construction_market_ai_update_buy = {"):]
        effect = effect[:effect.index("\n}")]
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

    def test_the_docs_keep_the_reading_the_removed_clause_went_on(self):
        # So that the purchase through the pause is not built a second time on the same guess.
        line = "TE_SELF_CHECK BROKEN construction_admin_while_paused country=BIC weeks=14 bought=420.0"
        self.assertIn(line, SYSTEM_DOC.read_text(encoding="utf-8"))
        playtest = PLAYTEST.read_text(encoding="utf-8")
        self.assertIn(line, playtest[playtest.index("## The AI's construction purchase fits its budget"):])

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
        fields = {name for name in named if not name.startswith("te_") and name not in NOT_PROBE_FIELDS}
        self.assertGreaterEqual(len(fields), 20)
        self.assertEqual(sorted(fields - logged), [])


# Backticked words in the play-test section that are not fields of the probe.
NOT_PROBE_FIELDS = {"main", "is_ai", "has_wasted_construction", "wasted_weeks", "spent", "repaid", "weeks"}


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
