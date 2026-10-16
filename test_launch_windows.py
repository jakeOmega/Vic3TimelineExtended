# -*- coding: utf-8 -*-
"""Launch windows for Solar System Colonization (Global Commons spec § 5).

scripts/generators/gen_launch_windows.py works out each window body's Hohmann
optima from Keplerian elements and an off-window premium curve from a Lambert
solver, and writes them as script. These tests hold:

- the method against history: every Mars launch since 1964 in its computed
  window, and Venus and Jupiter launches within four weeks of their optima;
- each premium curve's minimum inside its window, in the middle month for the
  bodies where the physics puts it there (the rest are listed, § 5.3's claim
  is about the method, and the physics wins);
- § 5.2a's Mars break-even table as the rule gives it with these premiums;
- the generated files: current, and, read back by a small interpreter of the
  script they use, equal to the computed windows for every month to END_DATE;
- the gate's script: every colony site maps to its body, its draw trigger
  reads that body, the setback cap applies to solar colonization only.
"""

import math
import os
import re
import sys
import unittest
from datetime import datetime

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import gen_launch_windows as glw  # noqa: E402

_PLANS = None


def plans():
    global _PLANS
    if _PLANS is None:
        _PLANS = glw.plan_all()
    return _PLANS


def plan(key):
    return next(p for p in plans()[0] if p.body.key == key)


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


# ---------------------------------------------------------------------------
# A small interpreter for the script the generator writes
# ---------------------------------------------------------------------------
_TOKEN = re.compile(r"#[^\n]*|<=|>=|!=|[{}=<>]|[^\s{}=<>#]+")


def _tokens(text):
    return [t for t in _TOKEN.findall(text) if not t.startswith("#")]


def _parse_block(tokens, i):
    """[(key, op, value)] up to the matching '}' (value: str or nested list)."""
    out = []
    while i < len(tokens) and tokens[i] != "}":
        key, op = tokens[i], tokens[i + 1]
        if tokens[i + 2] == "{":
            value, i = _parse_block(tokens, i + 3)
            i += 1
        else:
            value, i = tokens[i + 2], i + 3
        out.append((key, op, value))
    return out, i


def parse_file(text):
    tokens = _tokens(text)
    top, _ = _parse_block(tokens + ["}"], 0)
    return {key: value for key, _, value in top}


class Interpreter:
    """Evaluates the subset of script values and triggers the generated files
    use, at a given month: `year`, `te_history_month_index`, named values."""

    def __init__(self, values, triggers=None):
        self.values = values
        self.triggers = triggers or {}
        self.memo = {}

    def number(self, token, month):
        if token == "year":
            return month // 12
        if token == "te_history_month_index":
            return month
        if token in self.values:
            return self.value(token, month)
        return float(token)

    def test(self, block, month):
        ops = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b,
               ">=": lambda a, b: a >= b, "=": lambda a, b: a == b}
        for key, op, value in block:
            if key in self.triggers and value == "yes":
                if not self.test(self.triggers[key], month):
                    return False
            elif not ops[op](self.number(key, month), self.number(value, month)):
                return False
        return True

    def run(self, block, month, acc):
        taken = False
        for key, _, value in block:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    taken = False
                if taken:
                    continue
                body = value
                if key != "else":
                    limit = next(v for k, _, v in body if k == "limit")
                    if not self.test(limit, month):
                        continue
                taken = True
                acc = self.run([e for e in body if e[0] != "limit"], month, acc)
            elif key == "value":
                acc = self.number(value, month)
            elif key == "add":
                acc += self.number(value, month)
            elif key == "subtract":
                acc -= self.number(value, month)
            elif key == "multiply":
                acc *= self.number(value, month)
            elif key == "min":
                acc = max(acc, self.number(value, month))
            elif key == "max":
                acc = min(acc, self.number(value, month))
            elif key == "floor":
                acc = math.floor(acc + 1e-9)
            elif key == "round":
                acc = round(acc)
            else:
                raise AssertionError(f"unsupported script value step {key}")
        return acc

    def value(self, name, month):
        if (name, month) not in self.memo:
            self.memo[name, month] = self.run(self.values[name], month, 0)
        return self.memo[name, month]


def interpreter():
    values = parse_file(_raw("common", "script_values", "sr_launch_windows_generated.txt"))
    triggers = parse_file(_raw("common", "scripted_triggers", "sr_launch_windows_generated.txt"))
    return Interpreter(values, triggers)


# ---------------------------------------------------------------------------
# The method against history
# ---------------------------------------------------------------------------
class HistoryTest(unittest.TestCase):
    def test_every_mars_launch_since_1964_is_inside_its_window(self):
        mars = plan("mars")
        for name, date, window, days in glw.history_rows(mars):
            dt = datetime.strptime(date, "%Y-%m-%d")
            month = glw.month_index(dt.year, dt.month)
            with self.subTest(mission=name):
                self.assertTrue(window.start <= month <= window.end,
                                f"{name} {date} outside {glw.month_label(window.start)}–{glw.month_label(window.end)}")

    def test_venus_and_jupiter_launches_are_within_four_weeks_of_their_optima(self):
        for key in ("venus", "jupiter"):
            for name, date, window, days in glw.history_rows(plan(key)):
                with self.subTest(body=key, mission=name):
                    self.assertLessEqual(abs(days), 28, f"{name}: {days:+.0f} days from the optimum")

    def test_the_spec_s_prototype_optima_agree_within_four_days(self):
        # § 5.3's table, from a planets-only prototype. The generator's optima
        # run one to three days earlier; 1996's window moves a month with it.
        prototype = ("1964-11-23", "1971-06-06", "1975-09-13", "1996-12-01", "2003-06-24", "2005-08-16",
                     "2007-09-19", "2011-11-19", "2013-12-22", "2016-02-08", "2018-05-18", "2020-07-30")
        mars = plan("mars")
        for date in prototype:
            jd = glw.datetime_to_jd(datetime.strptime(date, "%Y-%m-%d"))
            nearest = min(mars.windows, key=lambda w: abs(w.optimum_jd - jd))
            with self.subTest(optimum=date):
                self.assertLessEqual(abs(nearest.optimum_jd - jd), 4)

    def test_mars_has_a_window_every_26_months_or_so(self):
        ws = plan("mars").windows
        gaps = [b.optimum_month - a.optimum_month for a, b in zip(ws, ws[1:])]
        self.assertTrue(all(24 <= g <= 28 for g in gaps), gaps)
        in_span = [w for w in ws if glw.month_index(1900, 1) <= w.optimum_month <= glw.month_index(2136, 1)]
        self.assertEqual(len(in_span), 111)  # § 5.3: "about 111 windows to 2136"


# ---------------------------------------------------------------------------
# Premium curves
# ---------------------------------------------------------------------------
# Bodies whose curve bottoms out in a window month either side of the middle
# one: the Hohmann-phase rule ignores the target's inclination and
# eccentricity, which shift the cheapest Lambert transfer by a few weeks
# (Venus 3.4 degrees, Ceres 10.6, Pallas 34.9, Pluto 17.1 and e 0.25).
OFF_MIDDLE = {"venus": -1, "ceres": 1, "pallas": 1, "kuiper": 1}


class PremiumCurveTest(unittest.TestCase):
    def test_each_curve_s_minimum_falls_in_its_window(self):
        for p in plans()[0]:
            best = min(p.extra_dv, key=lambda o: p.extra_dv[o])
            with self.subTest(body=p.body.key):
                self.assertIn(best, (-1, 0, 1))
                self.assertEqual(best, OFF_MIDDLE.get(p.body.key, 0),
                                 "the middle month, unless listed in OFF_MIDDLE")

    def test_window_months_are_free_and_every_other_month_costs(self):
        for p in plans()[0]:
            with self.subTest(body=p.body.key):
                for off, prem in p.premium.items():
                    if -1 <= off <= 1:
                        self.assertEqual(prem, 0.0)
                    else:
                        self.assertGreater(prem, 0.0)
                        self.assertLessEqual(prem, glw.PREMIUM_CAP)

    def test_premium_is_the_rocket_equation_on_the_mean_extra_delta_v(self):
        mars = plan("mars")
        for off in (-3, 2, 5):
            expected = round((math.exp(mars.extra_dv[off] / 3.7) - 1) * 100) / 100
            self.assertTrue(math.isclose(mars.premium[off], expected, rel_tol=1e-12))

    def test_mars_cheapest_transfer_matches_the_spec(self):
        # § 5.2a: "The minimum for Mars comes out at 4.45 km/s".
        lo, hi = plan("mars").best_dv
        self.assertGreater(lo, 4.2)
        self.assertLess(hi, 4.6)

    def test_premiums_rise_away_from_the_window(self):
        for p in plans()[0]:
            with self.subTest(body=p.body.key):
                self.assertLess(p.premium[2], p.premium[3])
                self.assertLess(p.premium[-2], p.premium[-3])


# ---------------------------------------------------------------------------
# The off-window rule (§ 5.2a)
# ---------------------------------------------------------------------------
class BreakEvenTest(unittest.TestCase):
    # (pace, approach) -> offsets of a 26-month Mars cycle with a launch, as the
    # rule gives them on the generated premiums. The spec's table came from a
    # prototype with gentler premiums; these are the physics' (report: c_report).
    EXPECTED = {
        (5, "standard"): [-1, 0, 1],
        (5, "ambitious"): [-1, 0, 1, 2],
        (10, "standard"): [-1, 0, 1, 2],
        (10, "ambitious"): [-1, 0, 1, 2],
        (20, "standard"): [-1, 0, 1, 2],
        (20, "ambitious"): [-1, 0, 1, 2, 3],
        (40, "standard"): [-1, 0, 1, 2, 3],
        (40, "ambitious"): [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    }

    def test_mars_table_comes_out_of_the_break_even_rule(self):
        premium = plan("mars").premium
        for (pace, approach), expected in self.EXPECTED.items():
            with self.subTest(pace=pace, approach=approach):
                self.assertEqual(glw.launch_offsets(premium, pace, approach), expected)

    def test_the_rule_by_hand(self):
        # goal x premium / pace <= k x m, m = months to the next free window.
        premium = plan("mars").premium
        for pace in (5, 10, 20, 40):
            for approach, k in (("standard", 1), ("ambitious", 2)):
                got = glw.launch_offsets(premium, pace, approach)
                for off in range(-12, 14):
                    m = 0 if -1 <= off <= 1 else (-1 - off if off < 0 else 25 - off)
                    launches = premium[off] == 0 or 400 * premium[off] / pace <= k * m
                    self.assertEqual(off in got, launches, (pace, approach, off))

    def test_shape_of_the_rule(self):
        premium = plan("mars").premium
        for pace in (5, 10, 20, 40):
            std = glw.launch_offsets(premium, pace, "standard")
            amb = glw.launch_offsets(premium, pace, "ambitious")
            self.assertTrue(set(std) <= set(amb), "Ambitious launches whenever Standard does")
            # It launches just after a window closes, never just before, at any
            # plausible pace: waiting is cheap then.
            self.assertFalse([o for o in amb if o < -1], (pace, amb))
        # Faster programmes launch off-window more often.
        counts = [len(glw.launch_offsets(premium, pace, "standard")) for pace in (5, 10, 20, 40)]
        self.assertEqual(counts, sorted(counts))


# ---------------------------------------------------------------------------
# The generated files
# ---------------------------------------------------------------------------
class GeneratedFilesTest(unittest.TestCase):
    def test_generated_files_are_current(self):
        result = glw.regenerate(dry_run=True)
        self.assertFalse(result["changed"],
                         f"stale: {result['changed_files']}; run python3 scripts/generators/gen_launch_windows.py")

    def test_one_bom_and_the_auto_generated_header(self):
        for rel in (glw.TRIGGERS_OUT, glw.VALUES_OUT):
            data = (glw.ROOT / rel).read_bytes()
            with self.subTest(file=str(rel)):
                self.assertTrue(data.startswith(b"\xef\xbb\xbf# AUTO-GENERATED"))
                self.assertFalse(data[3:].startswith(b"\xef\xbb\xbf"))

    def test_end_date_is_the_game_s(self):
        self.assertEqual(glw.end_date(), (2136, 1, 1))

    def test_the_script_reads_back_the_computed_windows_every_month(self):
        interp = interpreter()
        _, first, last = plans()
        for p in plans()[0]:
            key = p.body.key
            opens = set()
            for w in p.windows:
                opens.update(range(w.start, w.end + 1))
            optima = [w.optimum_month for w in p.windows]
            with self.subTest(body=key):
                for month in range(first, last + 1):
                    is_open = month in opens
                    nxt = next(o for o in optima if o + 1 >= month)
                    prev = max((o for o in optima if o < nxt), default=None)
                    to_next = max(0, nxt - 1 - month)
                    nearest = prev if prev is not None and month - prev <= nxt - month else nxt
                    self.assertEqual(interp.value(f"sr_window_months_to_next_{key}", month), to_next, month)
                    self.assertEqual(interp.test(interp.triggers[f"sr_window_open_{key}"], month), is_open, month)
                    offset = interp.value(f"sr_launch_offset_{key}", month)
                    self.assertEqual(offset, month - nearest, month)
                    premium = interp.value(f"sr_launch_premium_{key}", month)
                    self.assertAlmostEqual(premium, p.premium[month - nearest], places=6, msg=month)

    def test_generated_values_stay_inside_the_script_number_range(self):
        values = _raw("common", "script_values", "sr_launch_windows_generated.txt")
        numbers = [float(x) for x in re.findall(r"value = (-?[\d.]+)", values)]
        self.assertLess(max(numbers), 2_000_000)

    def test_files_stay_a_sane_size(self):
        size = sum((glw.ROOT / rel).stat().st_size for rel in (glw.TRIGGERS_OUT, glw.VALUES_OUT))
        self.assertLess(size, 400_000)


if __name__ == "__main__":
    unittest.main()
