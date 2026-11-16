"""What an AI government buys a week in a market game (te_construction_market_ai_purchase_target).

common/script_values/te_construction_market_ai_values.txt sets the purchase: the country's budget surplus over the
smoothed price, scaled by reserves and debt, or a floor if that is more, capped by the government queue. Until
2026-11-15 the floor was 10 points a week for every country, which was more than the whole weekly income of 23 of the
28 AI countries buying in February 1836; they borrowed to the engine's construction pause within months. The floor is
now a twentieth of fixed income, never more than the 10 points it was, paid from reserves (a tenth of itself with
none), and a fifth of fixed income higher while the country is short of bureaucracy, so such a country buys at least
a fifth. While the engine reports construction paused the purchase is nothing, except for a country short of
bureaucracy with a Government Administration level in its queue, which goes on buying that fifth
(docs/systems/mod_systems/construction.md, "The AI's purchase").

Nothing in the engine checks that script, so this runs the script's own text. What each part checks:

- ScriptAgainstModel runs the values through the evaluator of test_construction_market_budget_step.py, with the
  engine's reads (income, debt, reserves, the queue, the buildings) stubbed, against the same rule restated in Python
  (`model`). The restatement follows the script line by line, so it checks the script's operators and their order,
  and that a value does what its comment says; it would repeat a mistake in the rule itself.
- Surplus, Floor, TheAdministration, TheEvidence and TheLongRun are the independent checks: properties the rule must
  have whatever its wording (what it costs against income, that it never rises above the rule before, that the
  probe's sample countries spend no more than they have), and a week-by-week budget against the rule before.
- Constants holds the script's constants to the engine defines they are taken from.
- TheSelfCheck runs the weekly effects (the purchase, then TE_SELF_CHECK construction_admin_while_paused) over a
  country week by week, with a small runner for the few effects they use.

Run: python3 -m unittest test_construction_market_ai_purchase -v
"""
import itertools
import json
import math
import re
import unittest
from pathlib import Path

from test_construction_market_budget_step import CURRENT_VALUES, DISPLAY_VALUES, TARGET_VALUES, Env, load
from test_construction_market_site_sizing import TOKEN as EFFECT_TOKEN, code as effect_code, parse as parse_effects

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
SELFCHECK_POINTS = 400.0
ADMINISTRATION = "building_government_administration"
ADMINISTRATION_LEVELS = '"country_has_building_type_levels(bt:%s)"' % ADMINISTRATION
SELFCHECK = "construction_admin_while_paused"
SELFCHECK_VARS = ("levels", "states", "weeks", "bought", "wasted", "spent", "repaid")

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
        _PARSED["triggers"] = load(TRIGGERS)[1]
        items, _ = parse_effects(EFFECT_TOKEN.findall(effect_code(AI_EFFECTS)))
        _PARSED["effects"] = {key: value for key, _op, value in items}
    return _PARSED


class AiEnv(Env):
    """The shared evaluator with the AI values and the construction market's scripted triggers loaded too, the files
    parsed once, and a country's buildings to walk."""

    def __init__(self, names, variables, flags, buildings=(), globals_=frozenset()):
        parsed = _parsed()
        self.memo = {}
        self.constants, self.values, self.scripted = parsed["constants"], parsed["values"], parsed["triggers"]
        self.names, self.variables, self.flags, self.triggers = names, variables, flags, {}
        self.buildings, self.globals = buildings, globals_

    def operand(self, raw):
        # The engine's numbers have five decimals; the shared evaluator's floats carry noise past that, which a
        # comparison with 0 would read as a quantity.
        return round(super().operand(raw), 5)

    def one_cond(self, key, op, val):
        if key == "has_global_variable":
            return val in self.globals
        if key == "is_building_type":
            return self.names["its type"] == val
        if key == "any_scope_building":
            return any(building.env().cond(val) for building in self.buildings)
        if key in self.scripted:
            return self.cond(self.scripted[key]) == (val == "yes")
        return super().one_cond(key, op, val)


class Building:
    def __init__(self, kind, level=1, queued=0, under_construction=None):
        self.kind, self.level, self.queued = kind, level, queued
        self.under_construction = queued > 0 if under_construction is None else under_construction

    def env(self):
        return AiEnv({"its type": self.kind, "level": float(self.level),
                      "level_after_queued_constructions": float(self.level + self.queued)},
                     {}, flags={"is_under_construction": self.under_construction})


def administration(level=3, queued=1, **kwargs):
    """A country's buildings with a Government Administration that has `queued` levels in the queue."""
    return [Building("building_barracks", 5, 1), Building(ADMINISTRATION, level, queued, **kwargs)]


class Country:
    """One week of one government, as the script reads it."""

    def __init__(self, fixed_income, surplus, price=1250.0, reserves=0.0, debt=0.0, bureaucracy=50.0, queued=1,
                 weekly_max=20.0, paused=False, at_war=False, bubble=None, income=None, buildings=(), ai=True):
        self.fixed_income = float(fixed_income)
        self.surplus = float(surplus)  # net_fixed_income
        self.price = float(price)  # var:te_construction_market_price_stabilizer
        self.reserves, self.debt = reserves, debt  # scaled_gold_reserves, scaled_debt
        self.bureaucracy, self.queued, self.weekly_max = bureaucracy, queued, weekly_max
        self.paused, self.at_war, self.bubble = paused, at_war, bubble
        self.income = float(fixed_income if income is None else income)
        self.buildings, self.ai = list(buildings), ai
        self.states, self.site_levels, self.wasted, self.construction_bill = 4, 1, False, 0.0
        self.vars = {"te_construction_market_price_stabilizer": self.price}
        if bubble is not None:
            self.vars["bubble_pressure"] = bubble

    def administration_in_queue(self):
        return any(b.kind == ADMINISTRATION and (b.queued > 0 or b.under_construction) for b in self.buildings)

    def env(self, globals_=frozenset()):
        names = {
            "net_fixed_income": self.surplus,
            "fixed_income": self.fixed_income,
            "income": self.income,
            "fixed_expenses": self.fixed_income - self.surplus,
            "total_expenses": self.fixed_income - self.surplus + self.construction_bill,
            "scaled_gold_reserves": self.reserves,
            "scaled_debt": self.debt,
            "bureaucracy": self.bureaucracy,
            "construction_queue_num_queued_government_levels": float(self.queued),
            "modifier:country_max_weekly_construction_progress_add": self.weekly_max,
            "num_states": float(self.states),
            ADMINISTRATION_LEVELS: float(sum(b.level for b in self.buildings if b.kind == ADMINISTRATION)),
            # The levels of its Construction Sites that have a crew (the placement values' walk, not run here).
            "te_construction_market_site_levels": float(self.site_levels),
        }
        flags = {"is_construction_paused": self.paused, "is_at_war": self.at_war, "is_ai": self.ai,
                 "has_wasted_construction": self.wasted}
        return AiEnv(names, self.vars, flags, self.buildings, globals_)

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
    """The script's rule restated line by line (see the module's docstring for what that does and does not check)."""
    if c.queued <= 0:
        return 0.0
    if c.paused:
        if c.bureaucracy < 0 and c.administration_in_queue():
            return min(BUREAUCRACY_INCOME_SHARE * c.fixed_income / c.price, c.weekly_max)
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
        self.assertEqual(constants["TE_CONSTRUCTION_MARKET_AI_ADMIN_SELFCHECK_POINTS"], SELFCHECK_POINTS)

    def test_the_floor_is_the_margin_the_engines_budget_ai_defends(self):
        # Income under 1.05 times expenses is where it cuts wages and should-have spending: a surplus of 1 - 1/1.05,
        # 4.8% of income.
        for name in ("WAGE_CUT_INCOME_RATIO_THRESHOLD", "MONEY_SPENDING_MAX_RATIO_TO_REMOVE_SHOULD_HAVE"):
            self.assertAlmostEqual(FLOOR_INCOME_SHARE, 1 - 1 / NAI[name], delta=0.005, msg=name)

    def test_the_floor_is_whole_at_the_reserves_the_engine_asks_before_it_queues(self):
        self.assertEqual(FLOOR_FULL_RESERVES, NAI["CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS"])

    def test_the_part_on_credit_is_a_two_hundredth_of_income(self):
        self.assertAlmostEqual(FLOOR_INCOME_SHARE * FLOOR_MIN_FACTOR, 0.005)

    def test_the_engine_pauses_a_critical_construction_far_later_than_the_rest(self):
        # What the purchase through the pause leans on: the engine has a second, later pause.
        self.assertGreater(NAI["CONSTRUCTION_DEBT_PAUSE_CRITICAL_CONSTRUCTION"], 2 * NAI["CONSTRUCTION_DEBT_PAUSE"])

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

    def test_the_self_checks_points_are_four_administration_levels(self):
        # construction_cost_very_low, the base game's, which the mod does not redefine.
        path = _game_file("buildings/07_government.txt")
        if path is None:
            self.skipTest("no Victoria 3 install")
        text = path.read_text(encoding="utf-8-sig")
        body = text[text.index(ADMINISTRATION + " = {"):]
        self.assertRegex(body[:body.index("\n}")], r"required_construction\s*=\s*construction_cost_very_low\b")
        values = _game_file("script_values/building_values.txt").read_text(encoding="utf-8-sig")
        cost = float(re.search(r"^construction_cost_very_low\s*=\s*(\d+)", values, re.M).group(1))
        self.assertEqual(SELFCHECK_POINTS, 4 * cost)
        for path in sorted((ROOT / "common/script_values").glob("*.txt")):
            self.assertNotRegex(path.read_text(encoding="utf-8-sig"), r"(?m)^construction_cost_very_low\s*=")


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

    def test_paused_and_not_with_and_without_an_administration_queued(self):
        count = 0
        budgets = ((0.0, 0.0), (0.3, 0.0), (0.0, 0.45), (0.0, 0.9))  # reserves, debt
        queues = ((), administration(queued=0), administration(), administration(level=0),
                  administration(queued=2, under_construction=False))
        for (name, (fixed_income, price)), share, (reserves, debt), bureaucracy, paused, buildings, (queued, cap) in \
                itertools.product(ECONOMIES.items(), (-0.25, 0.03, 0.33), budgets, (50.0, -5.0), (False, True), queues,
                                  ((0, 20.0), (1, 10.0), (3, 20.0), (1, 140.0))):
            c = Country(fixed_income, share * fixed_income, price, reserves, debt, bureaucracy, queued, cap,
                        paused=paused, buildings=buildings)
            count += 1
            halls = [(b.level, b.queued) for b in buildings if b.kind == ADMINISTRATION]
            with self.subTest(economy=name, surplus=share, reserves=reserves, debt=debt, bureaucracy=bureaucracy,
                              paused=paused, administration=halls, queue=(queued, cap)):
                self.assertAlmostEqual(c.script(), model(c), delta=STEP)
        self.assertGreater(count, 3000)

    def test_it_is_not_rounded_to_whole_points(self):
        # A surplus of 143 a week (Kunduz's) buys a ninth of a point with no debt. Whole points made that nothing.
        self.assertAlmostEqual(Country(857.0, 143.0, 1249.0).script(), 143.0 / 1249.0, delta=STEP)
        self.assertNotIn("round", _code(AI_VALUES.read_text(encoding="utf-8-sig")))

    def test_with_an_empty_queue_it_buys_nothing(self):
        for paused, bureaucracy, buildings in itertools.product((False, True), (50.0, -50.0), ((), administration())):
            with self.subTest(paused=paused, bureaucracy=bureaucracy, administration=bool(buildings)):
                c = Country(75817.0, 30000.0, bureaucracy=bureaucracy, paused=paused, queued=0, buildings=buildings)
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
                        weekly_max=140.0, buildings=administration())
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

    def test_the_war_and_banking_brakes_do_not_touch_it(self):
        fixed_income, price = ECONOMIES["mid"]
        for reserves in (0.0, 0.05, 0.2):
            calm = Country(fixed_income, 0.0, price, reserves=reserves)
            shaken = Country(fixed_income, 0.0, price, reserves=reserves, at_war=True, bubble=80.0)
            with self.subTest(reserves=reserves):
                self.assertEqual(shaken.script(), calm.script())

    def test_a_queued_level_always_gets_something(self):
        # With no base construction in a market game, a purchase of nothing leaves the queue where it stands.
        for fixed_income, price in ((300.0, 1999.0), (857.0, 1249.0), (13678.0, 1265.0)):
            for share, debt in itertools.product((-2.0, -0.2, 0.0, 0.001), (0.0, 0.1, 0.39, 0.99)):
                c = Country(fixed_income, share * fixed_income, price, debt=debt)
                with self.subTest(fixed_income=fixed_income, surplus=share, debt=debt):
                    self.assertGreater(c.script(), 0.0005)

    def test_the_old_price_clamp_is_gone(self):
        code = _code(AI_VALUES.read_text(encoding="utf-8-sig"))
        floor = code[code.index("te_construction_market_ai_bureaucracy_purchase = {"):
                     code.index("te_construction_market_ai_purchase_target = {")]
        self.assertNotRegex(floor, r"\bmax\s*=\s*150\b")
        self.assertNotRegex(floor, r"\bvalue\s*=\s*income\b")
        self.assertNotIn("te_construction_market_price\n", floor)
        self.assertEqual(floor.count("var:te_construction_market_price_stabilizer"), 2)


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
        self.assertAlmostEqual(short.script_floor(), 0.1 * 0.05 * 11806.0 / 1369.0 + 0.2 * 11806.0 / 1369.0, delta=STEP)
        self.assertEqual(before(short), 26.0)


class TheAdministration(unittest.TestCase):
    """While the engine reports construction paused, one purchase goes on (owner, 2026-11-16)."""

    def paused(self, fixed_income=13678.0, price=1265.0, **kwargs):
        kwargs.setdefault("bureaucracy", -5.0)
        kwargs.setdefault("buildings", administration())
        return Country(fixed_income, kwargs.pop("surplus", 0.0), price, debt=kwargs.pop("debt", 0.5), paused=True,
                       **kwargs)

    def test_short_of_bureaucracy_with_one_queued_it_buys_the_fifth(self):
        for name in ("tiny", "mid"):
            fixed_income, price = ECONOMIES[name]
            for surplus, debt in itertools.product((-0.3, 0.0, 0.5), (0.41, 0.7, 0.98)):
                c = self.paused(fixed_income, price, surplus=surplus * fixed_income, debt=debt, weekly_max=140.0)
                with self.subTest(economy=name, surplus=surplus, debt=debt):
                    # On credit, whatever the reserves (none, in debt) and the surplus.
                    self.assertAlmostEqual(c.bill(), BUREAUCRACY_INCOME_SHARE * fixed_income, delta=STEP * price)

    def test_it_is_held_to_one_levels_weekly_maximum(self):
        # The rest of the queue is paused and could not use more.
        fixed_income, price = ECONOMIES["huge"]
        for queued in (1, 5):
            with self.subTest(queued=queued):
                self.assertAlmostEqual(self.paused(fixed_income, price, queued=queued, weekly_max=40.0).script(), 40.0,
                                       places=6)

    def test_every_other_paused_country_buys_nothing(self):
        cases = {
            "not short of bureaucracy": {"bureaucracy": 0.0},
            "no administration at all": {"buildings": ()},
            "an administration with nothing queued": {"buildings": administration(queued=0)},
            "another building queued": {"buildings": [Building("building_barracks", 2, 3)]},
            "an empty queue": {"queued": 0},
        }
        for name, kwargs in cases.items():
            with self.subTest(name):
                self.assertEqual(self.paused(surplus=5000.0, **kwargs).script(), 0.0)

    def test_either_read_of_the_queue_will_do(self):
        # A first level being built (level 0), an expansion with no progress the engine may not call under
        # construction, and a level it calls under construction without a count of queued levels.
        for buildings in (administration(level=0), administration(queued=2, under_construction=False),
                          administration(queued=0, under_construction=True)):
            with self.subTest(administration=[(b.level, b.queued, b.under_construction) for b in buildings][-1]):
                self.assertGreater(self.paused(buildings=buildings).script(), 0.0)

    def test_only_a_country_that_is_short_walks_its_buildings(self):
        trigger = _parsed()["triggers"]["te_construction_market_ai_building_administration"]
        self.assertEqual([key for key, _op, _value in trigger], ["bureaucracy", "any_scope_building"])

    def test_outside_the_pause_an_administration_in_the_queue_changes_nothing(self):
        for (fixed_income, price), share, bureaucracy in itertools.product(ECONOMIES.values(), (-0.2, 0.0, 0.4),
                                                                          (-5.0, 5.0)):
            with self.subTest(fixed_income=fixed_income, surplus=share, bureaucracy=bureaucracy):
                self.assertEqual(
                    Country(fixed_income, share * fixed_income, price, bureaucracy=bureaucracy,
                            buildings=administration()).script(),
                    Country(fixed_income, share * fixed_income, price, bureaucracy=bureaucracy).script())


class ThePurchaseReachesTheSites(unittest.TestCase):
    """te_construction_market_public_use_target, which sizes the sites, used to be nothing whenever paused."""

    def use(self, purchase=6.0, **kwargs):
        c = Country(13678.0, 0.0, 1265.0, **kwargs)
        c.vars["te_construction_market_public_target"] = purchase
        return c.env().value("te_construction_market_public_use_target")

    def test_an_ais_purchase_for_a_shortage_goes_through_the_pause(self):
        self.assertEqual(self.use(paused=True, bureaucracy=-5.0), 6.0)
        self.assertEqual(self.use(purchase=90.0, paused=True, bureaucracy=-5.0, queued=2, weekly_max=20.0), 40.0)

    def test_nothing_else_does(self):
        self.assertEqual(self.use(paused=True, bureaucracy=5.0), 0.0)
        self.assertEqual(self.use(paused=True, bureaucracy=-5.0, ai=False), 0.0)

    def test_unpaused_it_is_the_purchase_up_to_the_queues_cap_as_before(self):
        for ai, bureaucracy in itertools.product((True, False), (-5.0, 5.0)):
            with self.subTest(ai=ai, bureaucracy=bureaucracy):
                self.assertEqual(self.use(ai=ai, bureaucracy=bureaucracy), 6.0)
                self.assertEqual(self.use(purchase=90.0, ai=ai, bureaucracy=bureaucracy), 20.0)


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
        for share in (0.006, 0.06, 0.17, 0.33, 0.7):
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

    def test_with_no_surplus_at_all_the_part_on_credit_takes_decades_to_matter(self):
        # A two-hundredth of income a week, borrowed, with interest on it: under 2% of the ceiling after ten years
        # and a fifth after thirty, never paused, for about 19 points (0.6 a year: a 100-point level in 160 years).
        # The rule before was past the ceiling inside ten.
        self.assertLess(long_run(now, 3000.0, 0.0, 10).debt, 0.02)
        thirty = long_run(now, 3000.0, 0.0, 30)
        self.assertLess(thirty.debt, 0.25)
        self.assertEqual(thirty.paused_weeks, 0)
        self.assertAlmostEqual(thirty.by_year[-1], 19, delta=1)
        self.assertLessEqual(long_run(before, 3000.0, 0.0, 30).default_year, 10)


# ---------------------------------------------------------------------------
# The weekly effects, run: the purchase, then the self-check.
# ---------------------------------------------------------------------------
class Game:
    """Runs scripted effects of te_construction_market_ai_effects.txt on a country. It knows the effects that file
    uses and fails on any other."""

    def __init__(self):
        self.globals, self.log = set(), []

    def pulse(self, country):
        """What the weekly pulse runs for an AI country in a market game, in its order."""
        self.run("te_construction_market_ai_update_buy", country)
        self.run("te_construction_market_ai_admin_paused_selfcheck", country)

    def run(self, name, country):
        self.effect(_parsed()["effects"][name], country)

    def verdicts(self):
        return [line.split()[1] for line in self.log if line.startswith("TE_SELF_CHECK") and "START" not in line]

    def effect(self, items, c):
        taken = True
        for key, _op, value in items:
            if key in ("if", "else_if"):
                if key == "else_if" and taken:
                    continue
                taken = c.env(self.globals).cond(next(v for k, _o, v in value if k == "limit"))
                if taken:
                    self.effect([item for item in value if item[0] != "limit"], c)
            elif key == "else":
                if not taken:
                    self.effect(value, c)
                taken = True
            elif key == "set_variable":
                fields = {k: v for k, _o, v in value}
                c.vars[fields["name"]] = c.env(self.globals).operand(fields["value"])
            elif key == "change_variable":
                fields = {k: v for k, _o, v in value}
                assert fields["name"] in c.vars, "change_variable on unset %s does nothing" % fields["name"]
                c.vars[fields["name"]] += c.env(self.globals).operand(fields["add"])
            elif key == "remove_variable":
                assert value in c.vars, "remove_variable of unset %s" % value
                del c.vars[value]
            elif key == "set_global_variable":
                self.globals.add({k: v for k, _o, v in value}["name"])
            elif key == "debug_log":
                self.log.append(value.strip('"'))
            elif key == "debug_log_scopes":
                pass
            elif key in _parsed()["effects"] and value == "yes":
                self.effect(_parsed()["effects"][key], c)
            else:
                raise AssertionError("the runner does not know the effect %r" % key)


def paused_and_short(**kwargs):
    """A mid-size AI over 40% of its debt ceiling, short of bureaucracy, with an administration level queued and a
    Construction Site at work. A fifth of its income buys 9.5 points a week."""
    kwargs.setdefault("buildings", administration())
    return Country(60000.0, kwargs.pop("surplus", 1000.0), 1265.0, debt=0.5, bureaucracy=-8.0, paused=True, **kwargs)


def armed(c):
    return any(name.startswith("te_cm_chk_admin_") for name in c.vars)


class TheSelfCheck(unittest.TestCase):
    """TE_SELF_CHECK construction_admin_while_paused: does the engine build an administration through its pause?"""

    def weeks(self, game, country, count):
        for _ in range(count):
            game.pulse(country)

    def finish_the_level(self, country):
        hall = next(b for b in country.buildings if b.kind == ADMINISTRATION)
        hall.level, hall.queued, hall.under_construction = hall.level + 1, 0, False
        country.queued -= 1

    def test_the_pulse_sets_the_purchase_first(self):
        game, c = Game(), paused_and_short()
        game.pulse(c)
        self.assertAlmostEqual(c.vars["te_construction_market_public_target"], 0.2 * 60000.0 / 1265.0, delta=STEP)
        self.assertTrue(armed(c))
        self.assertEqual(game.log, [])

    def test_ok_when_a_level_finishes_while_paused(self):
        game, c = Game(), paused_and_short()
        self.weeks(game, c, 12)
        self.assertEqual(game.log, [])
        self.finish_the_level(c)
        game.pulse(c)
        self.assertEqual(game.verdicts(), ["OK"])
        self.assertEqual(game.log[0], "TE_SELF_CHECK START %s" % SELFCHECK)
        self.assertFalse(armed(c))

    def test_broken_once_four_levels_worth_was_bought_and_none_finished(self):
        game, c = Game(), paused_and_short()
        weekly = 0.2 * 60000.0 / 1265.0
        self.weeks(game, c, 1 + math.ceil(SELFCHECK_POINTS / weekly) - 1)
        self.assertEqual(game.log, [])
        game.pulse(c)
        self.assertEqual(game.verdicts(), ["BROKEN"])
        self.assertEqual(game.log[0], "TE_SELF_CHECK START %s" % SELFCHECK)
        self.assertFalse(armed(c))

    def test_the_line_carries_what_was_bought_and_what_it_cost(self):
        game, c = Game(), paused_and_short()
        c.wasted, c.construction_bill, c.income = True, 5000.0, 60400.0
        self.weeks(game, c, 4)
        self.assertEqual(c.vars["te_cm_chk_admin_weeks"], 3)
        self.assertEqual(c.vars["te_cm_chk_admin_wasted"], 3)
        self.assertAlmostEqual(c.vars["te_cm_chk_admin_bought"], 3 * 0.2 * 60000.0 / 1265.0, delta=3 * STEP)
        self.assertAlmostEqual(c.vars["te_cm_chk_admin_spent"], 3 * 5000.0, places=3)
        self.assertAlmostEqual(c.vars["te_cm_chk_admin_repaid"], 3 * 400.0, places=3)

    def test_a_small_country_takes_longer_and_is_judged_on_the_same_points(self):
        game, c = Game(), Country(3000.0, 100.0, 1250.0, debt=0.5, bureaucracy=-2.0, paused=True,
                                  buildings=administration())
        self.weeks(game, c, 800)  # 0.48 points a week
        self.assertEqual(game.log, [])
        self.weeks(game, c, 40)
        self.assertEqual(game.verdicts(), ["BROKEN"])

    def test_leaving_the_pause_decides_nothing(self):
        # Debt fell under the resume line: a level that finishes now proves nothing about the pause.
        game, c = Game(), paused_and_short()
        self.weeks(game, c, 5)
        c.paused, c.debt = False, 0.19
        self.finish_the_level(c)
        game.pulse(c)
        self.assertEqual(game.log, [])
        self.assertFalse(armed(c))

    def test_a_level_that_came_with_a_conquered_state_decides_nothing(self):
        game, c = Game(), paused_and_short()
        self.weeks(game, c, 5)
        c.states += 1
        c.buildings.append(Building(ADMINISTRATION, 2))
        game.pulse(c)
        self.assertEqual(game.log, [])
        self.assertFalse(armed(c))
        game.pulse(c)  # and it arms again on the new count
        self.assertTrue(armed(c))

    def test_a_shortage_that_ends_some_other_way_decides_nothing(self):
        game, c = Game(), paused_and_short()
        self.weeks(game, c, 5)
        c.bureaucracy = 3.0
        game.pulse(c)
        self.assertEqual(game.log, [])
        self.assertFalse(armed(c))

    def test_it_does_not_arm_without_each_thing_it_reads(self):
        cases = {
            "not paused": {"paused": False, "debt": 0.3},
            "not short": {"bureaucracy": 4.0},
            "no administration queued": {"buildings": administration(queued=0)},
            "no Construction Site with a crew": {"site_levels": 0},
        }
        for name, change in cases.items():
            game, c = Game(), paused_and_short()
            for field, value in change.items():
                setattr(c, field, value)
            self.weeks(game, c, 60)
            with self.subTest(name):
                self.assertEqual(game.log, [])
                self.assertFalse(armed(c))

    def test_once_a_game(self):
        game, first, second = Game(), paused_and_short(), paused_and_short()
        self.weeks(game, first, 3)
        self.weeks(game, second, 3)
        self.finish_the_level(first)
        game.pulse(first)
        self.assertEqual(game.verdicts(), ["OK"])
        self.finish_the_level(second)
        game.pulse(second)
        self.assertEqual(game.verdicts(), ["OK"])
        self.assertFalse(armed(second))
        third = paused_and_short()
        self.weeks(game, third, 60)
        self.assertEqual(game.verdicts(), ["OK"])
        self.assertFalse(armed(third))

    def test_each_line_can_be_rendered(self):
        # A templated debug_log the engine cannot render is dropped whole. These accessors are the ones the
        # construction site delivery check prints with (te_construction_market_update_effects.txt).
        effect = _code(AI_EFFECTS.read_text(encoding="utf-8-sig"))
        lines = re.findall(r'debug_log = "(TE_SELF_CHECK (?:OK|BROKEN) %s[^"]*)"' % SELFCHECK, effect)
        self.assertEqual(len(lines), 2)
        for line in lines:
            accessors = re.findall(r"\[([^\]]*)\]", line)
            self.assertEqual(accessors[0], "THIS.GetCountry.GetTagName")
            printed = [re.fullmatch(r"THIS\.Var\('te_cm_chk_admin_(\w+)'\)\.GetValue\|[01]", a) for a in accessors[1:]]
            self.assertTrue(all(printed), accessors)
            self.assertLessEqual({m.group(1) for m in printed}, set(SELFCHECK_VARS))
            self.assertNotIn("'", re.sub(r"\[[^\]]*\]", "", line))
        self.assertEqual(effect.count('debug_log = "TE_SELF_CHECK START %s"' % SELFCHECK), 2)

    def test_every_variable_it_counts_on_is_set_when_it_arms(self):
        game, c = Game(), paused_and_short()
        game.pulse(c)
        self.assertEqual({name[len("te_cm_chk_admin_"):] for name in c.vars if name.startswith("te_cm_chk_admin_")},
                         set(SELFCHECK_VARS))


class Wiring(unittest.TestCase):
    def test_only_an_ai_country_in_a_market_game_runs_it(self):
        pulse = PULSE.read_text(encoding="utf-8-sig")
        direct = pulse.index("te_direct_construction_on_weekly_pulse = yes")
        market = pulse.index("else_if = {", direct)
        call = pulse.index("te_construction_market_ai_update_buy = yes")
        self.assertLess(market, call)
        self.assertRegex(pulse[market:call], r"if = \{\s*limit = \{\s*is_ai = yes\s*\}\s*$")
        # ... and its self-check, in the same block, after the purchase is set.
        self.assertRegex(pulse[call:], r"^te_construction_market_ai_update_buy = yes\s+"
                                       r"te_construction_market_ai_admin_paused_selfcheck = yes\s+\}")
        for effect in ("te_construction_market_ai_update_buy", "te_construction_market_ai_admin_paused_selfcheck"):
            callers = [p.name for p in sorted((ROOT / "common").rglob("*.txt"))
                       if "%s = yes" % effect in p.read_text(encoding="utf-8-sig")]
            self.assertEqual(callers, [PULSE.name], effect)

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
        section = playtest[playtest.index("## The AI's construction purchase fits its budget"):]
        self.assertIn("`TE_SELF_CHECK … %s`" % SELFCHECK, section)
        self.assertIn("Fallback", section)

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
NOT_PROBE_FIELDS = {"main", "is_ai", "is_construction_paused", "is_under_construction", "wasted_weeks", "spent",
                    "repaid", "bought", "weeks", "bureaucracy"}


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
