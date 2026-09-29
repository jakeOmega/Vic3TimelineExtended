"""Fixed Budget's weekly step (te_construction_market_budget_shift_weeks).

The step size N comes from the engine's price formula, written out in
common/script_values/te_construction_market_target_values.txt. Nothing in the
engine checks that script, so this runs the script's own text: a small
evaluator for the script-value subset the chain uses (value / add / subtract /
multiply / divide / min / max, if / else_if / else with `limit`, the market
scope blocks, named values and constants) reads the real file, with the
engine's inputs (buy and sell orders, the price, the queue) stubbed. The
results are checked against a model written independently of the script: the
price formula itself, N worked out from it, and, for a small gap, N against
1 + e with e taken as a numeric derivative of the price. Arithmetic is rounded
to five decimals after every operation, as the engine's fixed-point numbers are.

It also pins the two defines the script mirrors (script cannot read defines).

Run: python3 -m unittest test_construction_market_budget_step -v
"""
import itertools
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFINES = ROOT / "common/defines/extra_defines.txt"
TARGET_VALUES = ROOT / "common/script_values/te_construction_market_target_values.txt"
CURRENT_VALUES = ROOT / "common/script_values/te_construction_market_current_values.txt"
DISPLAY_VALUES = ROOT / "common/script_values/te_construction_market_display_values.txt"

TOKEN = re.compile(r"<=|>=|!=|[{}=<>]|[^\s{}=<>!]+")


def tokenize(text):
    text = text.lstrip("﻿")
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0]
        out.extend(TOKEN.findall(line))
    return out


def parse_block(tokens, pos):
    """Items of a block as (key, op, value) in file order; value is a str or a list of items."""
    items = []
    while pos < len(tokens) and tokens[pos] != "}":
        key = tokens[pos]
        if pos + 1 < len(tokens) and tokens[pos + 1] in ("=", "<", ">", "<=", ">=", "!="):
            op = tokens[pos + 1]
            if tokens[pos + 2] == "{":
                value, pos = parse_block(tokens, pos + 3)
                pos += 1  # the closing brace
            else:
                value, pos = tokens[pos + 2], pos + 3
            items.append((key, op, value))
        else:
            raise ValueError(f"bare token {key!r}")
    return items, pos


def load(path):
    items, _ = parse_block(tokenize(path.read_text(encoding="utf-8")), 0)
    constants, values = {}, {}
    for key, _, value in items:
        if isinstance(value, list):
            values[key] = value
        else:
            constants[key] = float(value)
    return constants, values


class Env:
    """Evaluates script values from the real files against stubbed engine inputs."""

    QUANTUM = 1e-5  # the engine's fixed-point resolution

    def __init__(self, names, variables, flags, triggers):
        self.memo = {}
        self.constants, self.values = {}, {}
        for path in (TARGET_VALUES, CURRENT_VALUES, DISPLAY_VALUES):
            c, v = load(path)
            self.constants.update(c)
            self.values.update(v)
        self.names, self.variables, self.flags, self.triggers = names, variables, flags, triggers

    # -- operands -------------------------------------------------------------
    def operand(self, raw):
        if isinstance(raw, list):
            return self.body(raw, 0.0)
        try:
            return float(raw)
        except ValueError:
            pass
        if raw.startswith("var:"):
            return self.variables[raw[4:]]
        if raw in self.constants:
            return self.constants[raw]
        if raw in self.names:
            return self.names[raw]
        if raw in self.values:
            if raw not in self.memo:
                self.memo[raw] = self.body(self.values[raw], 0.0)
            return self.memo[raw]
        raise KeyError(f"unknown operand {raw!r}")

    def value(self, name):
        return self.operand(name)

    # -- conditions -----------------------------------------------------------
    def cond(self, items):
        return all(self.one_cond(k, op, v) for k, op, v in items)

    def one_cond(self, key, op, val):
        if key == "OR":
            return any(self.one_cond(k, o, v) for k, o, v in val)
        if key == "NOT":
            return not self.cond(val)
        if key == "has_variable":
            return val in self.variables
        if key in self.flags:
            return self.flags[key] == (val == "yes")
        if key in self.triggers:
            return self.triggers[key]() == (val == "yes")
        lhs, rhs = self.operand(key), self.operand(val)
        return {"=": lhs == rhs, "<": lhs < rhs, ">": lhs > rhs,
                "<=": lhs <= rhs, ">=": lhs >= rhs, "!=": lhs != rhs}[op]

    # -- bodies ---------------------------------------------------------------
    def body(self, items, x):
        chain_done = False
        for key, _, val in items:
            x = round(x / self.QUANTUM) * self.QUANTUM
            if key == "value":
                x = self.operand(val)
            elif key == "add":
                x += self.operand(val)
            elif key == "subtract":
                x -= self.operand(val)
            elif key == "multiply":
                x *= self.operand(val)
            elif key == "divide":
                d = self.operand(val)
                if d == 0:
                    raise ZeroDivisionError("script value divides by zero")
                x /= d
            elif key == "min":  # a floor
                x = max(x, self.operand(val))
            elif key == "max":  # a cap
                x = min(x, self.operand(val))
            elif key == "round":
                x = float(round(x))
            elif key in ("market", "mg:construction"):
                x = self.body(val, x)
            elif key in ("if", "else_if", "else"):
                if key == "if":
                    chain_done = False
                if not chain_done:
                    limit = next((v for k, _, v in val if k == "limit"), None)
                    if limit is None or self.cond(limit):
                        x = self.body([i for i in val if i[0] != "limit"], x)
                        chain_done = True
            elif key == "add" or key == "limit":
                pass
            else:
                raise ValueError(f"unsupported key {key!r}")
        return x


# ---------------------------------------------------------------------------
# The reference model: the engine's price formula, written from the defines.
# ---------------------------------------------------------------------------
R = 0.999  # PRICE_RANGE
F = 4.0    # BUY_SELL_DIFF_AT_MAX_FACTOR
SERVICES_PRICE = 1000.0


def price_factor(buy, sell):
    lo = min(buy, sell)
    imbalance = (buy - sell) / max(lo, 1e-9)
    return 1 + R * max(-1.0, min(1.0, imbalance / (F - 1)))


def elasticity(buy_others, goods, sell, h=1e-4):
    """d ln(price) / d ln(government goods), by central difference."""
    up = price_factor(buy_others + goods * (1 + h), sell)
    dn = price_factor(buy_others + goods * (1 - h), sell)
    return (math.log(up) - math.log(dn)) / (math.log(1 + h) - math.log(1 - h))


class State:
    """One week's inputs: the market's orders and the country's purchase."""

    def __init__(self, others, sell, scaling, quantity, budget, cap=1e12, paused=False):
        self.others, self.sell, self.scaling = others, sell, scaling
        self.quantity, self.budget, self.cap, self.paused = quantity, budget, cap, paused

    @property
    def goods_per_point(self):
        return max(1.0, 1.0 + self.scaling)

    def use(self):
        return 0.0 if self.paused else min(self.quantity, self.cap)

    def buy(self):
        return self.others + self.goods_per_point * self.use()

    def env(self):
        pricier = price_factor(self.buy(), self.sell) - 1.0
        names = {
            "market_goods_buy_orders": self.buy(),
            "market_goods_sell_orders": self.sell,
            "construction_cost_scaling_mult": self.scaling,
            "construction_queue_num_queued_government_levels": self.cap,
            "modifier:country_max_weekly_construction_progress_add": 1.0,
            "this.market.mg:construction.market_goods_pricier": pricier,
        }
        variables = {
            "te_construction_market_public_target": self.quantity,
            "te_construction_market_budget_quantity": self.quantity,
            "te_construction_market_public_budget": self.budget,
        }
        return Env(
            names, variables,
            flags={"is_construction_paused": self.paused},
            triggers={"te_construction_market_budget_mode_on": lambda: True},
        )

    def price_per_point(self):
        return SERVICES_PRICE * price_factor(self.buy(), self.sell) * self.goods_per_point

    def spend(self):
        return self.use() * self.price_per_point()


def next_quantity(state):
    return state.env().value("te_construction_market_budget_quantity_next_value")


class MirroredDefines(unittest.TestCase):
    def test_script_constants_match_extra_defines(self):
        defines = DEFINES.read_text(encoding="utf-8")

        def define(name):
            m = re.search(rf"^\s*{name}\s*=\s*([0-9.]+)", defines, re.M)
            self.assertIsNotNone(m, f"{name} missing from extra_defines.txt")
            return float(m.group(1))

        constants, _ = load(TARGET_VALUES)
        self.assertEqual(constants["TE_CONSTRUCTION_MARKET_PRICE_RANGE"], define("PRICE_RANGE"))
        self.assertEqual(constants["TE_CONSTRUCTION_MARKET_BUY_SELL_DIFF_AT_MAX_FACTOR"],
                         define("BUY_SELL_DIFF_AT_MAX_FACTOR"))

    def test_reference_model_uses_the_same_defines(self):
        constants, _ = load(TARGET_VALUES)
        self.assertEqual(R, constants["TE_CONSTRUCTION_MARKET_PRICE_RANGE"])
        self.assertEqual(F, constants["TE_CONSTRUCTION_MARKET_BUY_SELL_DIFF_AT_MAX_FACTOR"])

    def test_the_fixed_step_constant_is_gone(self):
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "gui").rglob("*.gui")):
            self.assertNotIn("TE_CONSTRUCTION_MARKET_BUDGET_SHIFT_WEEKS",
                             path.read_text(encoding="utf-8", errors="ignore"), str(path))


def reference_n(state):
    """N for one week, from the price model alone: the chord between the purchase in force and the
    purchase the budget wants, with a raise never spread over fewer than two weeks."""
    now = state.use()
    want = 0.0 if state.paused else min(state.budget / state.price_per_point() , state.cap)
    if abs(want - now) < 1e-9:
        n = 1.0
    else:
        gpp = state.goods_per_point
        pf_now = price_factor(state.others + gpp * now, state.sell)
        pf_want = price_factor(state.others + gpp * want, state.sell)
        n = max(1.0, 1 + want / (want - now) * (pf_want / pf_now - 1))
    if state.budget / state.price_per_point() > state.quantity:
        n = max(n, 2.0)
    return n


class StepSize(unittest.TestCase):
    def script_n(self, state):
        return state.env().value("te_construction_market_budget_shift_weeks")

    def test_script_step_equals_the_model_across_regimes(self):
        cases = {
            "shortage, small purchase": (300000, 180000, 3.0, 1000),
            "shortage, purchase dominates": (2000, 3000, 0.0, 2000),
            "surplus": (10000, 25000, 2.0, 300),
            "near the price floor": (10000, 39000, 2.0, 300),
            "at the price floor": (10000, 45000, 2.0, 300),
            "at the ceiling": (50000, 10000, 1.0, 500),
            "balanced": (5000, 6000, 1.0, 1000),
        }
        for name, (others, sell, scaling, q) in cases.items():
            base = State(others, sell, scaling, q, 0.0).spend()
            for factor in (0.1, 0.5, 2.0, 10.0):
                state = State(others, sell, scaling, q, factor * base)
                with self.subTest(name, factor=factor):
                    self.assertAlmostEqual(self.script_n(state), reference_n(state), delta=0.01 * reference_n(state))

    def test_for_a_small_gap_the_step_is_one_plus_the_price_elasticity(self):
        # A cut, so the raise floor does not apply. This is what ties the chord to the derivation:
        # N = 1 + e, where e is how much a 1% larger purchase raises the price, in %.
        for others, sell, scaling, q in ((300000, 180000, 5.2365, 1000), (2000, 3000, 0.0, 1000),
                                         (10000, 25000, 2.0, 300)):
            base = State(others, sell, scaling, q, 0.0).spend()
            state = State(others, sell, scaling, q, 0.999 * base)
            e = elasticity(others, state.goods_per_point * q, sell)
            with self.subTest(others=others, sell=sell):
                self.assertAlmostEqual(self.script_n(state), 1 + e, delta=max(0.02, 0.05 * e))

    def test_the_owners_screenshot_is_a_small_purchase_in_a_large_market(self):
        # 179,292 on sale, 325,239 wanted, 1,000 points bought at ~7,927 a point.
        scaling = 5.2365
        others = 325239.4 - 1000 * (1 + scaling)
        base = State(others, 179291.8, scaling, 1000.0, 0.0)
        self.assertAlmostEqual(base.price_per_point(), 7927, delta=15)
        self.assertAlmostEqual(elasticity(others, 1000 * (1 + scaling), 179291.8), 0.0091, places=3)
        # A cut is followed at once; a raise takes at least two weeks a step.
        self.assertAlmostEqual(self.script_n(State(others, 179291.8, scaling, 1000.0, 0.5 * base.spend())),
                               1.0, delta=0.05)
        self.assertEqual(self.script_n(State(others, 179291.8, scaling, 1000.0, 2 * base.spend())), 2.0)

    def test_a_raise_is_never_faster_than_a_half_step_and_a_cut_is_not_held_back(self):
        for others, sell in ((300000, 180000), (2000, 6000), (10000, 39000)):
            base = State(others, sell, 2.0, 1000, 0.0).spend()
            raise_n = self.script_n(State(others, sell, 2.0, 1000, 3 * base))
            cut_n = self.script_n(State(others, sell, 2.0, 1000, 0.3 * base))
            with self.subTest(others=others, sell=sell):
                self.assertGreaterEqual(raise_n, 2.0)
                self.assertGreaterEqual(cut_n, 1.0)
                self.assertLessEqual(cut_n, raise_n)

    def test_a_purchase_held_at_the_queue_cap_does_not_stall_the_step(self):
        # Both the purchase in force and the one the budget wants sit at the cap: nothing to
        # smooth, and no division of zero by zero.
        state = State(300000, 180000, 5.0, 4000.0, 1e9, cap=3000.0)
        self.assertEqual(self.script_n(state), 2.0)

    def test_paused_construction_buys_nothing_and_the_step_stays_finite(self):
        state = State(300000, 180000, 3.0, 1000, 8e6, paused=True)
        self.assertEqual(state.env().value("te_construction_market_budget_goods_now"), 0.0)
        self.assertEqual(state.env().value("te_construction_market_budget_goods_target"), 0.0)
        self.assertEqual(self.script_n(state), 2.0)

    def test_the_percent_the_panel_shows_is_a_hundred_over_the_step(self):
        state = State(300000, 180000, 5.0, 1000.0, 2 * 7.9e6)
        self.assertAlmostEqual(state.env().value("te_construction_market_display_budget_step_percent"), 50.0)


class WeeklyLoop(unittest.TestCase):
    """The script's own step, week by week, against a market that answers instantly."""

    def run_weeks(self, others, sell, scaling, q0, budget, weeks=20, cap=1e12):
        q = q0
        history = []
        for _ in range(weeks):
            q = next_quantity(State(others, sell, scaling, q, budget, cap=cap))
            history.append(State(others, sell, scaling, q, budget, cap=cap).spend())
        return history

    def scenarios(self, factors):
        for others, ratio, scaling, q0, factor in itertools.product(
                (2000, 300000), (0.3, 1.0, 4.0), (0.0, 5.0), (100, 1000), factors):
            sell = others * ratio
            base = State(others, sell, scaling, float(q0), 0.0, cap=20.0 * q0).spend()
            if base > 0:
                yield dict(others=others, sell=sell, scaling=scaling, q0=float(q0), cap=20.0 * q0,
                           budget=factor * base)

    def test_a_raise_lands_on_the_budget_without_spending_past_it(self):
        # Swept: 2,000 to 300,000 orders on other buyers; SELL from 0.3 to 4 times that (down to the
        # price floor); budgets 3 and 50 times today's. The worst overshoot in a sweep of about
        # 1,500 scenarios of the same model was 4.6%, for one week.
        for sc in self.scenarios((3, 50)):
            spends = self.run_weeks(sc["others"], sc["sell"], sc["scaling"], sc["q0"], sc["budget"], cap=sc["cap"])
            capped = sc["budget"] / State(sc["others"], sc["sell"], sc["scaling"], sc["q0"], 0.0).price_per_point() \
                > sc["cap"]
            with self.subTest(**sc):
                self.assertLessEqual(max(spends), sc["budget"] * 1.06)
                if not capped:
                    self.assertAlmostEqual(spends[-1] / sc["budget"], 1.0, delta=0.02)

    def test_a_cut_reaches_the_new_budget_within_a_few_weeks(self):
        for sc in self.scenarios((0.1, 0.5)):
            spends = self.run_weeks(sc["others"], sc["sell"], sc["scaling"], sc["q0"], sc["budget"], cap=sc["cap"])
            with self.subTest(**sc):
                self.assertLessEqual(max(spends), sc["budget"] * 1.25)
                self.assertAlmostEqual(spends[-1] / sc["budget"], 1.0, delta=0.02)

    def test_the_queue_cap_holds_spending_below_the_budget(self):
        spends = self.run_weeks(300000, 180000, 5.0, 1000.0, 2e8, cap=3000.0)
        state = State(300000, 180000, 5.0, 3000.0, 2e8, cap=3000.0)
        self.assertAlmostEqual(spends[-1], state.spend(), places=0)
        self.assertLess(spends[-1], 2e8)


if __name__ == "__main__":
    unittest.main()
