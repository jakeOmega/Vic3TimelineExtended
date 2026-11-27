"""What an AI government buys a week in a market game (te_construction_market_ai_purchase_target).

common/script_values/te_construction_market_ai_values.txt sets the purchase: the country's budget surplus over the
smoothed price, scaled by reserves and debt, or a floor if that is more, capped by the government queue. Until
2026-11-15 the floor was 10 points a week for every country, which was more than the whole weekly income of 23 of the
28 AI countries buying in February 1836; they borrowed to the engine's construction pause within months. The floor is
now a twentieth of fixed income, never more than the 10 points it was, paid from reserves (nothing with none) or,
up to a tenth of it, from the surplus, and a fifth of fixed income higher while the country is short of bureaucracy,
so such a country buys at least a fifth. A government with no surplus, no reserves and no such shortage buys nothing.
Since #1877 (owner, 2026-11-16) the interest rate moves the surplus term and the floor: at a high spread over the world
reference rate the country keeps a reserve of up to vanilla's tenth and spends only what is above it, at a low one it
may borrow up to a tenth of its debt ceiling, never more than a third of its surplus can carry at a high rate.
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
- TheRate and TheRateLongRun pin the rate's curve at its ends and its middle, the debt ceiling and what its interest
  can cost, that a crisis tightens it and a war takes the credit away, that it has no cliff, and, week by week, that
  the debt settles under the allowance, a high rate holds the reserve, and a rate that climbs on the debt has it paid
  down while the queue goes on being bought.
- Constants holds the script's constants to the engine defines they are taken from, and pins the one of those
  defines the mod sets (the reserve gate, 0.02 since #1877), which the floor's full reserves no longer follow.
- TheQueueRead runs the trigger the removed clause read its queue with, which the AI probe still reads.

Run: python3 -m unittest test_construction_market_ai_purchase -v
"""
import itertools
import json
import math
import re
import unittest
from pathlib import Path

from test_construction_market_budget_step import CURRENT_VALUES, DISPLAY_VALUES, TARGET_VALUES, Env, load
from vanilla_parsed import vanilla_define

ROOT = Path(__file__).resolve().parent
AI_VALUES = ROOT / "common/script_values/te_construction_market_ai_values.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_construction_market_triggers.txt"
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
# THE RATE (#1877, owner 2026-11-16): the reserve a government keeps and the debt it may run, by the spread of the rate
# it pays (var:te_rate_paid_pts) over the world reference rate (var:te_mon_era_base_now).
SPREAD_LOW, SPREAD_MID, SPREAD_HIGH = 2.0, 4.0, 7.0
RESERVE_MAX = 0.1
CREDIT_MAX = 0.1
RATE_GAIN = 2.0
CREDIT_SERVICE_SHARE = 0.33333
FIRST_ERA_BASE = 3.0  # what the stress rate stands on before the monetary update has run
# THE PASS (te_ai_build_pass_effects.txt).
PASS_SURPLUS_SHARE, PASS_SURPLUS_MIN, PASS_INNOVATION_SHARE = 0.16667, 15000.0, 0.9
PASS_DEBT_MAX, PASS_MAX_WEEKS, PASS_BACKOFF_DAYS, PASS_BUREAUCRACY_MARGIN = 0.1, 104.0, 365.0, 0.02
PASS_INFRASTRUCTURE_MARGIN, PASS_INDUSTRIAL_SHARE = 0.02, 0.1
# The credit's switch at 0, for the tests that read the rule without it.
NO_CREDIT = {"TE_CONSTRUCTION_MARKET_AI_CREDIT_MAX": 0.0}
# The construction costs of the buildings the pass queues: vanilla's construction_cost_medium (a university, a power
# plant), _very_low (an administration) and _very_high (a railway), and the mod's construction_cost_super_high (a
# highway, an airport). test_ai_build_pass.py holds each building's required_construction to its name.
UNIVERSITY_POINTS, ADMINISTRATION_POINTS = 400.0, 100.0
RAILWAY_POINTS, SUPER_HIGH_POINTS = 800.0, 2000.0
PASS_VALUES = ROOT / "common/script_values/te_ai_build_pass_values.txt"

# The engine's AI defines the constants are taken from, at vanilla's values (1.15.1, common/defines/00_ai.txt);
# test_matches_vanilla holds them to vanilla_parsed/defines.json. The mod leaves them alone for the reasoning to
# hold, except MOD_NAI's.
NAI = {
    "CONSTRUCTION_DEBT_PAUSE": 0.4,
    "CONSTRUCTION_DEBT_RESUME": 0.2,
    "CONSTRUCTION_DEBT_PAUSE_CRITICAL_CONSTRUCTION": 0.99,
    "CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS": 0.1,
    "WAGE_CUT_INCOME_RATIO_THRESHOLD": 1.05,
    "MONEY_SPENDING_MAX_RATIO_TO_REMOVE_SHOULD_HAVE": 1.05,
    # THE RATE's credit allowance and THE PASS's surplus test and innovation stop.
    "CHANGE_TAX_SIGNIFICANT_DEBT_THRESHOLD": 0.1,
    "MONEY_SPENDING_MIN_RATIO_TO_ADD_SHOULD_HAVE": 1.2,
    "MONEY_SPENDING_MIN_SURPLUS_TO_IGNORE_RATIO_FOR_SHOULD_HAVE": 15000,
    "MONEY_SPENDING_INNOVATION_DESIRED_THRESHOLD": 1.0,
}
# The one the mod sets (common/defines/extra_defines.txt, NAI): the reserve gate on a new construction, lowered from
# vanilla's 0.1 so that a government with a surplus queues without first saving a tenth (#1877; ai.md § AI Government
# Construction). The floor keeps vanilla's tenth (FLOOR_FULL_RESERVES): what the floor draws from reserves is not
# what the gate decides.
MOD_NAI = {
    "CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS": 0.02,
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

    def __init__(self, names, variables, flags, crisis=False, constants=None):
        parsed = _parsed()
        self.memo = {}
        # `constants` overrides the files' (a switch at another setting, for the model).
        self.constants = dict(parsed["constants"], **(constants or {})) if constants else parsed["constants"]
        self.values = parsed["values"]
        self.names, self.variables, self.flags = names, variables, flags
        # te_construction_market_triggers.txt: a Fixed Budget is on while this variable is set.
        budget_mode = "te_construction_market_budget_mode"
        self.triggers = {budget_mode + "_on": lambda: budget_mode in variables,
                         # te_monetary_triggers.txt: the cycle's panic or downturn, a peg losing confidence,
                         # hyperinflation.
                         "te_mon_in_financial_crisis": lambda: crisis}

    def operand(self, raw):
        # The engine's numbers have five decimals; the shared evaluator's floats carry noise past that, which a
        # comparison with 0 would read as a quantity.
        return round(super().operand(raw), 5)


class Country:
    """One week of one government, as the script reads it."""

    def __init__(self, fixed_income, surplus, price=1250.0, reserves=0.0, debt=0.0, bureaucracy=50.0, queued=1,
                 weekly_max=20.0, paused=False, at_war=False, bubble=None, income=None, rate=None, era=2.5,
                 credit=None, crisis=False, constants=None):
        self.fixed_income = float(fixed_income)
        self.surplus = float(surplus)  # net_fixed_income
        self.price = float(price)  # var:te_construction_market_price_stabilizer
        self.reserves, self.debt = reserves, debt  # scaled_gold_reserves, scaled_debt
        self.bureaucracy, self.queued, self.weekly_max = bureaucracy, queued, weekly_max
        self.paused, self.at_war, self.bubble = paused, at_war, bubble
        self.income = float(fixed_income if income is None else income)  # read by the rule before only
        # The rate paid and the world reference rate (var:te_rate_paid_pts, var:te_mon_era_base_now), both absent
        # until the monetary update has run; the debt ceiling (`credit`), about 320 weeks of a large economy's fixed
        # income in the 1925-1947 run; a financial crisis (te_mon_in_financial_crisis).
        self.rate, self.era, self.crisis = rate, era, crisis
        self.credit = 320.0 * self.fixed_income if credit is None else float(credit)
        self.constants = constants
        self.vars = {"te_construction_market_price_stabilizer": self.price}
        if bubble is not None:
            self.vars["bubble_pressure"] = bubble
        if rate is not None:
            self.vars["te_rate_paid_pts"] = float(rate)
            self.vars["te_mon_era_base_now"] = float(era)

    def env(self):
        names = {
            "net_fixed_income": self.surplus,
            "fixed_income": self.fixed_income,
            "scaled_gold_reserves": self.reserves,
            "scaled_debt": self.debt,
            "bureaucracy": self.bureaucracy,
            "construction_queue_num_queued_government_levels": float(self.queued),
            "modifier:country_max_weekly_construction_progress_add": self.weekly_max,
            "credit": self.credit,
            "construction_cost_medium": UNIVERSITY_POINTS,
            "construction_cost_very_low": ADMINISTRATION_POINTS,
            "construction_cost_very_high": RAILWAY_POINTS,
            "construction_cost_super_high": SUPER_HIGH_POINTS,
        }
        # The evaluator fails on a read it has no stub for. There is none for is_ai, for a building or for income
        # that is not fixed: the purchase and the sites' use of it may read none of them.
        return AiEnv(names, self.vars, flags={"is_construction_paused": self.paused, "is_at_war": self.at_war},
                     crisis=self.crisis, constants=self.constants)

    def script(self):
        return self.env().value("te_construction_market_ai_purchase_target")

    def script_floor(self):
        return self.env().value("te_construction_market_ai_purchase_floor")

    def bill(self):
        return self.script() * self.price


def clamp01(x):
    return max(0.0, min(1.0, x))


def model_spread(c):
    spread = SPREAD_MID if c.rate is None else c.rate - c.era
    return max(spread, SPREAD_HIGH) if c.crisis else spread


def model_required(c):
    return RESERVE_MAX * clamp01((model_spread(c) - SPREAD_MID) / (SPREAD_HIGH - SPREAD_MID))


def model_ease(c):
    """The curve's low side, 0 to 1; nothing at war or while bubble pressure is 50 or more."""
    if c.at_war or (c.bubble is not None and c.bubble >= 50):
        return 0.0
    return clamp01((SPREAD_MID - model_spread(c)) / (SPREAD_MID - SPREAD_LOW))


def model_service_cap(c):
    stress = ((FIRST_ERA_BASE if c.rate is None else c.era) + SPREAD_HIGH) / 100
    return max(c.surplus, 0.0) * 52 * CREDIT_SERVICE_SHARE / stress / max(c.credit, 1.0)


def model_allowance(c, credit_max=None):
    credit_max = CREDIT_MAX if credit_max is None else credit_max
    return min(credit_max * model_ease(c), model_service_cap(c))


def model_tolerance(c, debt_max=None):
    """te_ai_build_pass_debt_tolerance: the debt the pass still queues for, on the same curve."""
    debt_max = PASS_DEBT_MAX if debt_max is None else debt_max
    return min(debt_max * model_ease(c), model_service_cap(c))


def model_factor(c):
    required = model_required(c)
    allowance = model_allowance(c, (c.constants or {}).get("TE_CONSTRUCTION_MARKET_AI_CREDIT_MAX"))
    factor = 1 + c.reserves - c.debt
    factor += RATE_GAIN * max(0.0, allowance - c.debt)
    factor -= min(c.reserves, required) + RATE_GAIN * max(0.0, required - c.reserves)
    if c.at_war and c.reserves < 0.5:
        factor -= 0.5 - c.reserves
    if c.bubble is not None and c.bubble >= 50 and c.reserves < 0.3:
        factor -= 0.3 - c.reserves
    return max(factor, 0.1)


def model_floor(c):
    whole = min(FLOOR_MAX_POINTS, FLOOR_INCOME_SHARE * c.fixed_income / c.price)
    from_reserves = whole * clamp01((c.reserves - model_required(c)) / FLOOR_FULL_RESERVES)
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

    def test_the_floor_is_whole_at_vanillas_reserve_gate(self):
        # Vanilla's tenth, which an AI had to hold before it could queue a government building: the floor was whole
        # wherever a queue could start. The mod's gate is lower now, so a queue can start where the floor pays a
        # fifth to all of it; the floor keeps the tenth and so draws reserves no faster than before at any level.
        self.assertEqual(FLOOR_FULL_RESERVES, NAI["CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS"])
        self.assertLess(MOD_NAI["CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS"], FLOOR_FULL_RESERVES)

    def test_the_mod_sets_the_reserve_gate_once_below_vanillas_and_above_none(self):
        # Above 0: the engine still asks for reserves past the building's cost. Under vanilla's 0.1: the point.
        sets = []
        for path in sorted(DEFINES_DIR.glob("*.txt")):
            text = "\n".join(line.split("#", 1)[0] for line in path.read_text(encoding="utf-8-sig").splitlines())
            for name, value in MOD_NAI.items():
                for m in re.finditer(rf"\b{name}\s*=\s*([0-9.]+)", text):
                    sets.append((path.name, name, float(m.group(1))))
        self.assertEqual(sets, [("extra_defines.txt", name, value) for name, value in MOD_NAI.items()])
        for name, value in MOD_NAI.items():
            self.assertGreater(value, 0, name)
            self.assertLess(value, NAI[name], name)
        nai = re.search(r"(?ms)^NAI\s*=\s*\{(.*?)^\}", (DEFINES_DIR / "extra_defines.txt").read_text(encoding="utf-8-sig"))
        self.assertIsNotNone(nai)
        for name in MOD_NAI:
            self.assertRegex(nai.group(1), rf"(?m)^\t{name}\s*=", f"{name} is not in the NAI block")

    def test_the_rate_and_the_pass_hold_the_numbers_this_file_models(self):
        constants = _parsed()["constants"]
        for name, value in (("SPREAD_LOW", SPREAD_LOW), ("SPREAD_MID", SPREAD_MID), ("SPREAD_HIGH", SPREAD_HIGH),
                            ("RESERVE_MAX", RESERVE_MAX), ("CREDIT_MAX", CREDIT_MAX), ("RATE_GAIN", RATE_GAIN),
                            ("CREDIT_SERVICE_SHARE", CREDIT_SERVICE_SHARE)):
            self.assertEqual(constants["TE_CONSTRUCTION_MARKET_AI_" + name], value, name)
        for name, value in (("SURPLUS_SHARE", PASS_SURPLUS_SHARE), ("SURPLUS_MIN", PASS_SURPLUS_MIN),
                            ("INNOVATION_SHARE", PASS_INNOVATION_SHARE), ("DEBT_MAX", PASS_DEBT_MAX),
                            ("MAX_WEEKS", PASS_MAX_WEEKS), ("BACKOFF_DAYS", PASS_BACKOFF_DAYS),
                            ("BUREAUCRACY_MARGIN", PASS_BUREAUCRACY_MARGIN),
                            ("INFRASTRUCTURE_MARGIN", PASS_INFRASTRUCTURE_MARGIN),
                            ("INDUSTRIAL_SHARE", PASS_INDUSTRIAL_SHARE)):
            self.assertEqual(constants["TE_AI_BUILD_PASS_" + name], value, name)

    def test_the_pass_tolerates_the_debt_the_credit_allows_for_the_same_reasons(self):
        # Apart so that the credit's switch at 0 leaves the pass reaching a debtor; equal as built.
        self.assertEqual(PASS_DEBT_MAX, CREDIT_MAX)
        # Two years, at 1,250 a point and a surplus of a sixth of fixed income: a university or a power plant from
        # 28,800 a week of fixed income, an administration from 7,200, a railway from 57,700, a highway or an airport
        # from 144,200 (the values file's figures).
        for points, income in ((UNIVERSITY_POINTS, 28800.0), (ADMINISTRATION_POINTS, 7200.0),
                               (RAILWAY_POINTS, 57700.0), (SUPER_HIGH_POINTS, 144200.0)):
            self.assertAlmostEqual(points * 1250.0 / (income / 6), PASS_MAX_WEEKS, delta=0.5)
        # The points are the game's: vanilla's three and the mod's.
        vanilla = json.loads((ROOT / "vanilla_parsed/common/script_values.json").read_text(encoding="utf-8"))
        for name, points in (("construction_cost_medium", UNIVERSITY_POINTS),
                             ("construction_cost_very_low", ADMINISTRATION_POINTS),
                             ("construction_cost_very_high", RAILWAY_POINTS)):
            self.assertEqual(float(vanilla[name][1]), points, name)
        mod = (ROOT / "common/script_values/extra_script_values.txt").read_text(encoding="utf-8-sig")
        self.assertRegex(mod, r"(?m)^construction_cost_super_high = 2000$")

    def test_the_rates_numbers_stand_where_their_comments_say(self):
        self.assertLess(SPREAD_LOW, SPREAD_MID)
        self.assertLess(SPREAD_MID, SPREAD_HIGH)
        # At a high rate the reserve vanilla's gate asked for, which the floor is whole at.
        self.assertEqual(RESERVE_MAX, NAI["CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS"])
        self.assertEqual(RESERVE_MAX, FLOOR_FULL_RESERVES)
        # The most credit is the debt the engine's AI still calls insignificant; it settles two-thirds of the way.
        self.assertEqual(CREDIT_MAX, NAI["CHANGE_TAX_SIGNIFICANT_DEBT_THRESHOLD"])
        self.assertAlmostEqual(RATE_GAIN / (1 + RATE_GAIN) * CREDIT_MAX, 0.0667, delta=0.0001)
        # Half the pause's resume line, a quarter of the pause, under the monetary system's debt-load premium.
        self.assertLessEqual(CREDIT_MAX, NAI["CONSTRUCTION_DEBT_RESUME"] / 2)
        self.assertLessEqual(CREDIT_MAX, NAI["CONSTRUCTION_DEBT_PAUSE"] / 4)
        premium = re.search(r"(?ms)^te_mon_scaled_debt_premium = \{\n(.*?)^\}",
                            (ROOT / "common/script_values/te_monetary_script_values.txt").read_text(encoding="utf-8-sig"))
        self.assertRegex(premium.group(1), r"value = scaled_debt\s+subtract = 0\.25\b")
        self.assertLess(CREDIT_MAX, 0.25)
        self.assertAlmostEqual(CREDIT_SERVICE_SHARE, 1 / 3, delta=0.00001)

    def test_the_pass_asks_for_the_surplus_the_engines_budget_ai_asks_for(self):
        # Income 1.2 times expenses is a surplus of a sixth of income; or a surplus of 15,000 whatever the ratio.
        self.assertAlmostEqual(PASS_SURPLUS_SHARE, 1 - 1 / NAI["MONEY_SPENDING_MIN_RATIO_TO_ADD_SHOULD_HAVE"],
                               delta=0.00001)
        self.assertEqual(PASS_SURPLUS_MIN, NAI["MONEY_SPENDING_MIN_SURPLUS_TO_IGNORE_RATIO_FOR_SHOULD_HAVE"])
        self.assertGreater(1 - 1 / NAI["MONEY_SPENDING_MAX_RATIO_TO_REMOVE_SHOULD_HAVE"], 0)
        self.assertLess(PASS_INNOVATION_SHARE, NAI["MONEY_SPENDING_INNOVATION_DESIRED_THRESHOLD"])

    def test_the_part_the_surplus_pays_is_a_two_hundredth_of_income(self):
        self.assertAlmostEqual(FLOOR_INCOME_SHARE * FLOOR_MIN_FACTOR, 0.005)

    def test_the_mod_leaves_those_defines_at_the_engines_values(self):
        # A mod define that moves one of them moves what the formula's constants stand on: revisit both together.
        for path in sorted(DEFINES_DIR.glob("*.txt")):
            text = "\n".join(line.split("#", 1)[0] for line in path.read_text(encoding="utf-8-sig").splitlines())
            for name in (n for n in NAI if n not in MOD_NAI):
                self.assertIsNone(re.search(rf"\b{name}\s*=", text), f"{path.name} sets {name}")

    def test_matches_vanilla(self):
        # vanilla_parsed/defines.json (#1879), so it runs in CI too.
        for name, value in NAI.items():
            self.assertEqual(float(vanilla_define("NAI", name)), value, name)


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

    def test_across_rates_crises_and_wars(self):
        count = 0
        # The bubble's brake and the era are each varied once, at one rate; the brakes add to the rate's terms.
        for (name, (fixed_income, price)), share, (reserves, debt), (rate, era, bubble), crisis, at_war, weeks in \
                itertools.product(ECONOMIES.items(), (-0.25, 0.0, 0.03, 0.25, 0.7),
                                  ((0.0, 0.0), (0.03, 0.0), (0.1, 0.0), (0.4, 0.0), (0.0, 0.03), (0.0, 0.067),
                                   (0.0, 0.2), (0.0, 0.45)),
                                  [(r, 2.5, None) for r in (None, 0.5, 3.5, 4.5, 5.5, 6.5, 8.0, 9.5, 12.0, 25.0)]
                                  + [(3.5, 2.0, None), (8.0, 2.0, None), (3.5, 2.5, 60.0), (12.0, 2.5, 60.0)],
                                  (False, True), (False, True), (120.0, 320.0)):
            c = Country(fixed_income, share * fixed_income, price, reserves, debt, at_war=at_war, bubble=bubble,
                        rate=rate, era=era, crisis=crisis, credit=weeks * fixed_income)
            count += 1
            with self.subTest(economy=name, surplus=share, reserves=reserves, debt=debt, rate=rate, era=era,
                              crisis=crisis, at_war=at_war, bubble=bubble, credit_weeks=weeks):
                self.assertAlmostEqual(c.script(), model(c), delta=STEP)
        self.assertGreater(count, 10000)

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


ADMINISTRATION = "building_government_administration"
QUEUE_READ = "te_construction_market_ai_building_administration"


class QueueEnv(AiEnv):
    """The evaluator with the construction market's scripted triggers and a country's buildings to walk."""

    def __init__(self, names, flags, buildings=()):
        super().__init__(names, {}, flags)
        self.buildings = buildings
        if "triggers" not in _PARSED:
            _PARSED["triggers"] = load(TRIGGERS)[1]

    def one_cond(self, key, op, val):
        if key == "is_building_type":
            return self.names["its type"] == val
        if key == "any_scope_building":
            return any(building.env().cond(val) for building in self.buildings)
        if key in _PARSED["triggers"]:
            return self.cond(_PARSED["triggers"][key]) == (val == "yes")
        return super().one_cond(key, op, val)


class Building:
    def __init__(self, kind, level=1, queued=0, under_construction=None):
        self.kind, self.level, self.queued = kind, level, queued
        self.under_construction = queued > 0 if under_construction is None else under_construction

    def env(self):
        return QueueEnv({"its type": self.kind, "level": float(self.level),
                         "level_after_queued_constructions": float(self.level + self.queued)},
                        flags={"is_under_construction": self.under_construction})


def administration(level=3, queued=1, **kwargs):
    """A country's buildings with a Government Administration that has `queued` levels in the queue."""
    return [Building("building_barracks", 5, 1), Building(ADMINISTRATION, level, queued, **kwargs)]


class TheQueueRead(unittest.TestCase):
    """te_construction_market_ai_building_administration: short of bureaucracy with a Government Administration level
    in the queue. The purchase read it while it bought through the pause; the AI probe's cm_admin still does."""

    def reads(self, bureaucracy=-5.0, buildings=()):
        return QueueEnv({"bureaucracy": bureaucracy}, {}, buildings).cond([(QUEUE_READ, "=", "yes")])

    def test_either_read_of_the_queue_will_do(self):
        # A level queued on a standing building, a first level being built (level 0), an expansion with no progress
        # the engine may not call under construction, and a level it calls under construction without a count of
        # queued levels.
        for buildings in (administration(), administration(level=0),
                          administration(queued=2, under_construction=False),
                          administration(queued=0, under_construction=True)):
            with self.subTest(administration=[(b.level, b.queued, b.under_construction) for b in buildings][-1]):
                self.assertTrue(self.reads(buildings=buildings))

    def test_it_needs_the_shortage_and_the_queued_administration(self):
        cases = {
            "not short of bureaucracy": {"bureaucracy": 0.0, "buildings": administration()},
            "no administration at all": {"buildings": ()},
            "an administration with nothing queued": {"buildings": administration(queued=0)},
            "another building queued": {"buildings": [Building("building_barracks", 2, 3)]},
        }
        for name, kwargs in cases.items():
            with self.subTest(name):
                self.assertFalse(self.reads(**kwargs))

    def test_only_a_country_that_is_short_walks_its_buildings(self):
        self.assertEqual([key for key, _op, _value in load(TRIGGERS)[1][QUEUE_READ]],
                         ["bureaucracy", "any_scope_building"])

    def test_the_probe_is_its_only_caller(self):
        callers = [p.name for p in sorted((ROOT / "common").rglob("*.txt"))
                   if "%s = yes" % QUEUE_READ in p.read_text(encoding="utf-8-sig")]
        self.assertEqual(callers, ["te_ai_probe_values.txt"],
                         "the purchase must not read it again; and once the AI probe is gone, remove the trigger, "
                         "te_construction_market_building_queued_levels and this class with it")


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
    def __init__(self, by_year, debt, paused_weeks, default_year, reserves=0.0, max_debt=0.0, debt_by_year=()):
        self.by_year, self.debt, self.paused_weeks, self.default_year = by_year, debt, paused_weeks, default_year
        self.reserves, self.max_debt, self.debt_by_year = reserves, max_debt, list(debt_by_year)


def long_run(rule, fixed_income, surplus_share, years, price=PRICE, paid=None, tax_raise=0.0, rate=None, era=2.5,
             returns=0.0, weekly_max=20.0):
    """Points bought by the end of each year, the debt share at the end, the weeks paused, the year of default.
    `tax_raise` is what the engine's budget AI might add to income, as a share of it, once debt is over a tenth of
    the ceiling (NAI CHANGE_TAX_SIGNIFICANT_DEBT_THRESHOLD). `rate`, the rate paid in points a year (a number, or a
    function of the year from 1), is what the purchase reads and what the debt costs; without it the purchase reads
    no rate and the debt costs RATE.

    `returns` is what a point of government construction adds to fixed income each year from then on, as a share of
    what it cost, all of it surplus: 0 by default, so the model has no growth (what was built earns nothing) unless
    it is set. The debt ceiling and the reserve limit follow fixed income. `weekly_max` is a level's weekly maximum,
    the purchase's cap with one level queued; a run with returns lifts it, since its surplus grows."""
    gold = debt = points = max_debt = earned = 0.0
    paused, paused_weeks, by_year, default_year, debt_by_year = False, 0, [], None, []
    for week in range(1, years * 52 + 1):
        income = fixed_income + earned
        ceiling, limit = CEILING_WEEKS * income, RESERVE_WEEKS * income
        gold = min(gold, limit)
        share = debt / ceiling
        now_rate = rate(math.ceil(week / 52)) if callable(rate) else rate
        cost = RATE if now_rate is None else now_rate / 100
        surplus = (surplus_share * fixed_income + earned - cost * debt / 52
                   + (tax_raise * fixed_income if share > 0.1 else 0.0))
        if paused and share <= NAI["CONSTRUCTION_DEBT_RESUME"]:
            paused = False
        elif not paused and share >= NAI["CONSTRUCTION_DEBT_PAUSE"]:
            paused = True
        paused_weeks += paused
        bought = rule(Country(income, surplus, price, gold / limit, share, weekly_max=weekly_max, paused=paused,
                              rate=now_rate, era=era, credit=ceiling))
        points += bought
        earned += returns * bought * (paid or price) / 52
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
        max_debt = max(max_debt, debt / ceiling)
        if week % 52 == 0:
            by_year.append(points)
            debt_by_year.append(debt / ceiling)
    return Run(by_year, debt / ceiling, paused_weeks, default_year, gold / limit, max_debt, debt_by_year)


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


def values(c, *names):
    env = c.env()
    return [env.value(name) for name in names]


CURVE = ("te_construction_market_ai_required_reserves", "te_construction_market_ai_credit_allowance")


class TheRate(unittest.TestCase):
    """The reserve a government keeps and the debt it may run, by the rate it pays (THE RATE in the values file)."""

    def rich(self, spread, era=2.5, **kwargs):
        # A surplus large enough that the allowance's service cap does not bind.
        return Country(75817.0, 0.4 * 75817.0, 1256.0, rate=era + spread, era=era, **kwargs)

    def test_with_no_rate_and_at_the_middle_it_is_the_rule_as_it_was(self):
        for (name, (fixed_income, price)), share, (reserves, debt), at_war, bubble in itertools.product(
                ECONOMIES.items(), (-0.25, 0.03, 0.25), ((0.0, 0.0), (0.06, 0.0), (0.4, 0.0), (0.0, 0.05), (0.0, 0.3)),
                (False, True), (None, 60.0)):
            none = Country(fixed_income, share * fixed_income, price, reserves, debt, at_war=at_war, bubble=bubble)
            middle = Country(fixed_income, share * fixed_income, price, reserves, debt, at_war=at_war, bubble=bubble,
                             rate=2.5 + SPREAD_MID)
            with self.subTest(economy=name, surplus=share, reserves=reserves, debt=debt):
                self.assertEqual(values(none, *CURVE), [0.0, 0.0])
                self.assertAlmostEqual(none.script(), middle.script(), delta=STEP)
                factor = max(1 + reserves - debt - (0.5 - reserves if at_war and reserves < 0.5 else 0)
                             - (0.3 - reserves if bubble and reserves < 0.3 else 0), 0.1)
                whole = min(FLOOR_MAX_POINTS, FLOOR_INCOME_SHARE * fixed_income / price)
                floor = max(whole * clamp01(reserves / FLOOR_FULL_RESERVES),
                            min(max(share * fixed_income, 0) / price, whole * FLOOR_MIN_FACTOR))
                self.assertAlmostEqual(none.script(), min(max(max(share * fixed_income, 0) / price * factor, floor),
                                                          20.0), delta=STEP)

    def test_the_curve_at_its_ends_and_its_middle(self):
        for spread, required, allowance in (
                (-3.0, 0.0, CREDIT_MAX), (SPREAD_LOW, 0.0, CREDIT_MAX), ((SPREAD_LOW + SPREAD_MID) / 2, 0.0, CREDIT_MAX / 2),
                (SPREAD_MID, 0.0, 0.0), ((SPREAD_MID + SPREAD_HIGH) / 2, RESERVE_MAX / 2, 0.0),
                (SPREAD_HIGH, RESERVE_MAX, 0.0), (20.0, RESERVE_MAX, 0.0)):
            for era in (3.0, 2.5, 2.0):
                with self.subTest(spread=spread, era=era):
                    got = values(self.rich(spread, era), *CURVE)
                    self.assertAlmostEqual(got[0], required, delta=0.0001)
                    self.assertAlmostEqual(got[1], allowance, delta=0.0001)

    def test_it_reads_the_spread_over_the_reference_rate_not_the_rate(self):
        # The same 4.5% is a low spread when the world's safe rate is 3 and a middling one at 2.
        self.assertGreater(values(Country(75817.0, 30000.0, rate=4.5, era=3.0), CURVE[1])[0],
                           values(Country(75817.0, 30000.0, rate=4.5, era=2.0), CURVE[1])[0])

    def test_a_financial_crisis_reads_as_a_high_rate_whatever_the_rate(self):
        for spread in (-2.0, SPREAD_LOW, SPREAD_MID, 6.0):
            with self.subTest(spread=spread):
                self.assertEqual(values(self.rich(spread, crisis=True), *CURVE), [RESERVE_MAX, 0.0])
                # So a crisis never buys more than the same country outside it.
                for reserves, debt in ((0.0, 0.0), (0.05, 0.0), (0.0, 0.05)):
                    calm = Country(75817.0, 20000.0, 1256.0, reserves, debt, rate=2.5 + spread)
                    hit = Country(75817.0, 20000.0, 1256.0, reserves, debt, rate=2.5 + spread, crisis=True)
                    self.assertLessEqual(hit.script(), calm.script() + STEP)

    def test_no_credit_at_war_or_in_a_bubble(self):
        # Where the war brake and the banking brake hold the purchase back, no credit offsets them.
        self.assertEqual(values(self.rich(-2.0, at_war=True), CURVE[1]), [0.0])
        for bubble, allowed in ((49.0, True), (50.0, False), (80.0, False)):
            with self.subTest(bubble=bubble):
                self.assertEqual(values(self.rich(-2.0, bubble=bubble), CURVE[1])[0] > 0, allowed)
        # So at high bubble pressure with no reserves the factor is the old rule's 0.7 at a low rate too.
        surplus = 0.4 * 75817.0
        c = self.rich(-2.0, bubble=60.0, queued=9, weekly_max=200.0)
        self.assertAlmostEqual(c.script() / (surplus / 1256.0), 1 - 0.3, delta=0.0002)

    def test_no_cliff_anywhere_along_the_curve(self):
        # 0.01 of a point of spread moves the factor by at most RATE_GAIN x CREDIT_MAX / 200 = 0.001 at the credit end
        # and RATE_GAIN x RESERVE_MAX / 300 at the reserve end.
        for reserves, debt in ((0.0, 0.0), (0.04, 0.0), (0.0, 0.03)):
            last = None
            for step in range(-300, 1300):
                c = Country(75817.0, 20000.0, 1256.0, reserves, debt, queued=4, weekly_max=200.0,
                            rate=2.5 + step / 100)
                now = c.script()
                if last is not None:
                    with self.subTest(reserves=reserves, debt=debt, spread=step / 100):
                        self.assertLessEqual(abs(now - last), 0.0011 * 20000.0 / 1256.0 + 2 * STEP)
                last = now

    def test_the_allowance_costs_at_most_a_third_of_the_surplus_at_the_rate_high_asks(self):
        for share, weeks, era in itertools.product((0.001, 0.01, 0.03, 0.1, 0.25, 0.5), (60.0, 120.0, 320.0, 700.0),
                                                   (3.0, 2.5, 2.0)):
            c = Country(10000.0, share * 10000.0, rate=era, era=era, credit=weeks * 10000.0)
            allowance = values(c, CURVE[1])[0]
            with self.subTest(surplus=share, ceiling_weeks=weeks, era=era):
                self.assertLessEqual(allowance, CREDIT_MAX)
                interest = allowance * c.credit * (era + SPREAD_HIGH) / 100
                # The script's five decimals: an allowance is a multiple of 0.00001 of the ceiling.
                self.assertLessEqual(interest, share * 10000.0 * 52 / 3 * 1.001 + 0.00001 * c.credit * 0.1)
        # A country with no surplus may borrow nothing, whatever the rate.
        self.assertEqual(values(Country(10000.0, 0.0, rate=0.5, era=2.5), CURVE[1]), [0.0])
        self.assertEqual(values(Country(10000.0, -500.0, rate=0.5, era=2.5), CURVE[1]), [0.0])

    def test_at_a_low_rate_it_borrows_a_fifth_of_its_surplus_at_most_and_none_past_the_allowance(self):
        surplus = 0.4 * 75817.0
        self.assertAlmostEqual(self.rich(0.0, queued=9, weekly_max=200.0).script(),
                               surplus / 1256.0 * (1 + RATE_GAIN * CREDIT_MAX), delta=STEP)
        for debt in (0.0, 0.03, 0.0667, 0.1, 0.2):
            c = Country(75817.0, surplus, 1256.0, 0.0, debt, queued=9, weekly_max=200.0, rate=2.5)
            factor = c.script() / (surplus / 1256.0)
            with self.subTest(debt=debt):
                self.assertLessEqual(factor, 1 + RATE_GAIN * CREDIT_MAX + 0.0001)
                # It spends more than the surplus only under the balance point, two-thirds of the allowance.
                self.assertEqual(factor > 1 + 0.0001, debt < RATE_GAIN / (1 + RATE_GAIN) * CREDIT_MAX - 0.0001)

    def test_at_a_high_rate_it_saves_toward_the_reserve_and_spends_only_what_is_above_it(self):
        surplus = 0.25 * 75817.0
        for reserves, factor in ((0.0, 1 - RATE_GAIN * RESERVE_MAX), (0.05, 1 - RATE_GAIN * 0.05), (RESERVE_MAX, 1.0),
                                 (0.3, 1 + 0.3 - RESERVE_MAX)):
            c = Country(75817.0, surplus, 1256.0, reserves, queued=9, weekly_max=200.0, rate=2.5 + 9.0)
            with self.subTest(reserves=reserves):
                self.assertAlmostEqual(c.script(), surplus / 1256.0 * factor, delta=STEP)
        # The floor does not spend the reserve asked for either: with no surplus and reserves of 0.1, nothing.
        self.assertEqual(Country(75817.0, 0.0, 1256.0, RESERVE_MAX, rate=2.5 + 9.0).script(), 0.0)
        self.assertGreater(Country(75817.0, 0.0, 1256.0, RESERVE_MAX, rate=2.5 + SPREAD_MID).script(), 0.0)

    def test_when_the_rate_rises_on_its_debt_it_stops_borrowing_and_pays_down_but_goes_on_buying(self):
        surplus = 0.25 * 75817.0
        balance = RATE_GAIN / (1 + RATE_GAIN) * CREDIT_MAX
        for spread in (SPREAD_MID, 5.5, SPREAD_HIGH, 12.0):
            c = Country(75817.0, surplus, 1256.0, 0.0, balance, queued=9, weekly_max=200.0, rate=2.5 + spread)
            factor = c.script() / (surplus / 1256.0)
            with self.subTest(spread=spread):
                self.assertLess(factor, 1.0)
                self.assertGreaterEqual(factor, FLOOR_MIN_FACTOR)
        # At a high rate it keeps 0.73 of what it bought at the middle with no debt.
        high = Country(75817.0, surplus, 1256.0, 0.0, balance, queued=9, weekly_max=200.0, rate=2.5 + SPREAD_HIGH)
        self.assertAlmostEqual(high.script() / (surplus / 1256.0), 1 - balance - RATE_GAIN * RESERVE_MAX, delta=0.0002)


class TheCreditSwitch(unittest.TestCase):
    """CREDIT_MAX is the credit's switch: at 0 nothing else changes but the credit."""

    def test_at_zero_there_is_no_credit_at_any_rate(self):
        for spread in (-3.0, SPREAD_LOW, 3.0, SPREAD_MID):
            c = Country(75817.0, 0.4 * 75817.0, 1256.0, rate=2.5 + spread, constants=NO_CREDIT)
            with self.subTest(spread=spread):
                self.assertEqual(values(c, CURVE[1]), [0.0])

    def test_at_zero_a_low_rate_is_the_middle_and_a_high_rate_still_asks_for_its_reserve(self):
        for reserves, debt, spread in itertools.product(((0.0, 0.0), (0.05, 0.0), (0.0, 0.05)), [0],
                                                        (-3.0, SPREAD_LOW, 3.0, 9.0)):
            (res, dbt) = reserves
            off = Country(75817.0, 20000.0, 1256.0, res, dbt, queued=9, weekly_max=200.0, rate=2.5 + spread,
                          constants=NO_CREDIT)
            middle = Country(75817.0, 20000.0, 1256.0, res, dbt, queued=9, weekly_max=200.0, rate=2.5 + SPREAD_MID)
            on = Country(75817.0, 20000.0, 1256.0, res, dbt, queued=9, weekly_max=200.0, rate=2.5 + spread)
            with self.subTest(reserves=res, debt=dbt, spread=spread):
                if spread <= SPREAD_MID:
                    self.assertAlmostEqual(off.script(), middle.script(), delta=STEP)
                else:
                    self.assertAlmostEqual(off.script(), on.script(), delta=STEP)
                self.assertAlmostEqual(off.script(), model(off), delta=STEP)

    def test_at_zero_a_low_rate_never_borrows_in_the_long_run(self):
        def no_credit(c):
            c.constants = NO_CREDIT
            return c.script()
        for share in (0.06, 0.17, 0.5):
            run = long_run(no_credit, 3000.0, share, 30, rate=2.5 + 1.0)
            with self.subTest(surplus=share):
                self.assertLess(run.max_debt, 1e-6)


class TheRateLongRun(unittest.TestCase):
    """long_run's budget, a level always queued, with the rate read and paid. long_run has no growth unless
    `returns` is set: what is built earns nothing, so building sooner is worth nothing to it but the points."""

    LOW, HIGH = 2.5 + 1.0, 2.5 + 9.0

    def test_at_a_low_rate_the_debt_settles_at_two_thirds_of_the_allowance_and_never_nears_the_pause(self):
        for share in (0.06, 0.17, 0.25, 0.5):
            run = long_run(now, 3000.0, share, 40, rate=self.LOW)
            with self.subTest(surplus=share):
                self.assertLessEqual(run.max_debt, RATE_GAIN / (1 + RATE_GAIN) * CREDIT_MAX + 0.001)
                self.assertEqual(run.paused_weeks, 0)
                self.assertIsNone(run.default_year)

    def test_at_a_low_rate_it_builds_more_than_at_the_middle_by_about_what_it_borrowed(self):
        for share in (0.06, 0.17, 0.25, 0.5):
            low = long_run(now, 3000.0, share, 30, rate=self.LOW)
            middle = long_run(now, 3000.0, share, 30, rate=2.5 + SPREAD_MID)
            borrowed = low.debt * CEILING_WEEKS * 3000.0 / PRICE
            with self.subTest(surplus=share):
                self.assertGreater(low.by_year[-1], middle.by_year[-1])
                # The extra points are the debt less thirty years of interest on it, never more than the debt.
                self.assertLessEqual(low.by_year[-1] - middle.by_year[-1], borrowed + 1)
                self.assertLess(middle.debt, 1e-6)

    def test_with_a_level_always_queued_the_debt_stands_at_two_thirds_of_the_allowance_for_good(self):
        # The factor is 1 there, so nothing pays it down while a level is queued (the reviewer, 2026-11-16). It
        # climbs toward the balance, more slowly as it nears it (0.043 at ten years, 0.064 at thirty, 0.066 at fifty
        # with a surplus of 17%), and never comes down.
        balance = RATE_GAIN / (1 + RATE_GAIN) * CREDIT_MAX
        for share in (0.17, 0.25):
            run = long_run(now, 3000.0, share, 100, rate=self.LOW)
            debts = [run.debt_by_year[year - 1] for year in (10, 30, 50, 100)]
            with self.subTest(surplus=share):
                self.assertEqual(debts, sorted(debts))
                self.assertGreater(debts[1], 0.9 * balance)
                self.assertAlmostEqual(debts[3], balance, delta=0.0002)

    def low_less_middle(self, share, returns=0.0):
        kwargs = dict(returns=returns, weekly_max=1e6) if returns else {}
        low = long_run(now, 3000.0, share, 100, rate=self.LOW, **kwargs)
        middle = long_run(now, 3000.0, share, 100, rate=2.5 + SPREAD_MID, **kwargs)
        return {year: low.by_year[year - 1] - middle.by_year[year - 1] for year in (10, 30, 50, 100)}

    def test_with_no_return_the_credit_is_ahead_at_first_and_behind_from_about_year_50(self):
        # It buys 16.7 weeks of income (40 points at 1,250) sooner and pays interest on them from then on: about
        # 1.4 points a year at 3.5%, so its lead is gone in about thirty years and it falls behind. Nobody should read
        # this as a verdict either way: the model has no growth, and growth is what the credit is for.
        diff = self.low_less_middle(0.17)
        for year, points in ((10, 20.5), (30, 9.1), (50, -16.7), (100, -86.3)):
            self.assertAlmostEqual(diff[year], points, delta=0.5)
        diff = self.low_less_middle(0.25)
        self.assertEqual([diff[y] > 0 for y in (10, 30, 50, 100)], [True, True, False, False])

    def test_with_a_return_above_the_rate_it_stays_ahead(self):
        # A point that adds 4.5% of its cost a year to the surplus, a point above the 3.5% the debt costs.
        for share in (0.06, 0.17, 0.25):
            diff = self.low_less_middle(share, returns=0.045)
            with self.subTest(surplus=share):
                self.assertTrue(all(diff[y] > 0 for y in (10, 30, 50, 100)), diff)
                self.assertGreater(diff[100], diff[50])

    def test_the_return_it_needs_is_about_the_rate_paid(self):
        # Behind by year 100 at a return of 2.5%, ahead at 3.5%, the rate the debt costs: the ceiling grows with
        # income, so the credit's pounds grow too and the break-even is a little under the rate.
        for share in (0.17, 0.25):
            with self.subTest(surplus=share):
                self.assertLess(self.low_less_middle(share, returns=0.025)[100], 0)
                below = self.low_less_middle(share, returns=0.035)
                self.assertGreater(below[50], 0)
                self.assertGreater(below[100], 0)

    def test_at_a_high_rate_it_holds_the_reserve_and_never_borrows(self):
        for share in (0.06, 0.17, 0.25):
            run = long_run(now, 3000.0, share, 30, rate=self.HIGH)
            with self.subTest(surplus=share):
                self.assertLess(run.max_debt, 1e-6)
                self.assertGreater(run.reserves, 0.95 * RESERVE_MAX)
                self.assertGreater(run.by_year[-1], 0.9 * 30 * share * 3000.0 * 52 / PRICE)

    def test_a_rate_that_climbs_on_its_debt_is_paid_down_while_it_goes_on_building(self):
        def climbs(year):
            return self.LOW if year <= 10 else self.HIGH
        for share in (0.06, 0.17, 0.25):
            run = long_run(now, 3000.0, share, 30, rate=climbs)
            with self.subTest(surplus=share):
                # A thin surplus borrows little: the allowance is what a third of it can carry at the high rate.
                self.assertGreater(run.debt_by_year[9], 0.005)
                self.assertLess(run.debt_by_year[-1], run.debt_by_year[9] / 2)
                self.assertEqual(run.paused_weeks, 0)
                gains = [b - a for a, b in zip([0.0] + run.by_year, run.by_year)]
                self.assertTrue(all(g > 0 for g in gains), gains)


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


if __name__ == "__main__":
    unittest.main()
