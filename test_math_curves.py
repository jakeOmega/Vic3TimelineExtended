# -*- coding: utf-8 -*-
"""te_sqrt (common/script_values/te_math_generated.txt, gen_math_curves.py).

The engine logs nothing when a script value's arithmetic is off, so the
committed tree is parsed and evaluated here, in floats and in the engine's
five-decimal fixed point, against math.sqrt across its range.
"""

import importlib.util
import math
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(REPO, "common", "script_values", "te_math_generated.txt")
HELPERS = os.path.join(REPO, "common", "scripted_effects", "te_math_effects.txt")

_spec = importlib.util.spec_from_file_location(
    "gen_math_curves", os.path.join(REPO, "scripts", "generators", "gen_math_curves.py"))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _parse(tokens, i):
    """A brace block's (key, value) pairs in order, and the index past its `}`."""
    pairs = []
    while tokens[i] != "}":
        key, op = tokens[i], tokens[i + 1]
        if tokens[i + 2] == "{":
            value, i = _parse(tokens, i + 3)
        else:
            value, i = tokens[i + 2], i + 3
        pairs.append((key, value) if op == "=" else ("compare", (key, op, value)))
    return pairs, i + 1


def tree(text, name="te_sqrt"):
    """A script value's parsed body: (key, value) pairs, a limit's comparisons as ("compare", (lhs, op, rhs))."""
    tokens = re.findall(r"[{}]|[<>]=?|=|[^\s{}<>=]+", re.sub(r"#[^\n]*", "", text))
    start = next(i for i in range(len(tokens)) if tokens[i:i + 3] == [name, "=", "{"])
    return _parse(tokens, start + 3)[0]


def _cut(x):
    """The engine's fixed point: five decimals, toward zero (rounded first at the sixth, so a float's
    0.99999999 of a unit counts as the unit it stands for)."""
    return math.trunc(round(x * 100000, 6)) / 100000


OPS = {"value": lambda v, n: n, "add": lambda v, n: v + n, "subtract": lambda v, n: v - n,
       "multiply": lambda v, n: v * n, "divide": lambda v, n: v / n}
COMPARE = {"<": lambda a, b: a < b, ">": lambda a, b: a > b, "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b}


def evaluate(block, x, fixed=False, value=0.0, depth=0):
    """(value, deepest if) of a script value of literals and var:te_math_in, with if/else_if/else."""
    lit = (lambda t: x if t == "var:te_math_in" else float(t))
    deepest, taken = depth, False
    for key, arg in block:
        if key in ("if", "else_if", "else"):
            if key == "if":
                taken = False
            if taken:
                continue
            limit = dict(arg).get("limit", [])
            if key != "else" and not all(COMPARE[op](lit(a), lit(b)) for _, (a, op, b) in limit):
                continue
            taken = True
            value, d = evaluate([p for p in arg if p[0] != "limit"], x, fixed, value, depth + 1)
            deepest = max(deepest, d)
        else:
            value = OPS[key](value, lit(arg))
            if fixed:
                value = _cut(value)
    return value, deepest


def _samples(lo, hi, n):
    return [lo * (hi / lo) ** (i / (n - 1)) for i in range(n)]


class TeSqrtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _read(OUT)
        cls.tree = tree(cls.text)
        cls.top = gen.knots()[-1]

    def sqrt(self, x, fixed=False):
        return evaluate(self.tree, x, fixed)[0]

    def error(self, x, fixed):
        """te_sqrt's relative error at x, which the engine would hold to five decimals in fixed point."""
        x = _cut(x) if fixed else x
        return abs(self.sqrt(x, fixed) / math.sqrt(x) - 1)

    def test_the_committed_file_is_current(self):
        self.assertEqual(self.text, gen.render(), "run scripts/generators/gen_math_curves.py")

    def test_one_bom(self):
        with open(OUT, "rb") as f:
            raw = f.read(6)
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))

    def test_one_branch_per_segment(self):
        """A binary tree of n leaves has n - 1 splits, plus the outer `> 0`."""
        self.assertEqual(self.text.count("limit = {"), len(gen.segments()))

    def test_within_its_stated_error(self):
        for fixed in (False, True):
            for x in _samples(0.001, self.top, 4000):
                with self.subTest(x=x, fixed=fixed):
                    self.assertLess(self.error(x, fixed), 0.005)
            for x in _samples(0.00001, 0.001, 400):
                with self.subTest(x=x, fixed=fixed):
                    self.assertLess(self.error(x, fixed), 0.02)

    def test_under_the_root_to_the_top_knot(self):
        for x in _samples(0.00001, self.top, 4000):
            with self.subTest(x=x):
                self.assertLessEqual(self.sqrt(x), math.sqrt(x) * (1 + 1e-5) + 1e-5)

    def test_rising(self):
        xs = [0.0] + _samples(0.00001, self.top * 4, 6000)
        ys = [self.sqrt(x) for x in xs]
        self.assertEqual(ys, sorted(ys))

    def test_zero_and_below(self):
        for x in (0.0, -1.0, -1e9):
            with self.subTest(x=x):
                self.assertEqual(self.sqrt(x), 0.0)

    def test_exact_at_powers_of_two(self):
        for k in range(0, 17):
            with self.subTest(x=2 ** k):
                self.assertAlmostEqual(self.sqrt(2 ** k), math.sqrt(2 ** k), places=4)

    def test_small_counts(self):
        """Decolonization's backers (decol_iw_refresh_fighters) read it at whole numbers."""
        for n in range(1, 13):
            with self.subTest(n=n):
                self.assertLess(self.error(n, True), 0.004)

    def test_no_cap(self):
        """Past the top knot the last segment carries on: the curve never flattens."""
        self.assertGreater(self.sqrt(self.top * 1.3), self.sqrt(self.top))

    def test_a_read_is_a_few_comparisons(self):
        depths = {evaluate(self.tree, x)[1] for x in _samples(0.00001, self.top, 500)}
        self.assertLessEqual(max(depths), 9)

    def test_knots_sit_on_the_engine_grid(self):
        for k in gen.knots():
            with self.subTest(k=k):
                self.assertEqual(round(k * 100000), k * 100000)
        self.assertLess(gen.knots()[-1], 9.2e13)


class HelperTests(unittest.TestCase):
    def test_te_set_sqrt_sets_reads_and_removes_the_input(self):
        text = re.sub(r"#[^\n]*", "", _read(HELPERS))
        body = text[text.index("te_set_sqrt = {"):]
        steps = [body.index(s) for s in ("name = te_math_in value = $IN$", "name = $OUT$ value = te_sqrt",
                                          "remove_variable = te_math_in")]
        self.assertEqual(steps, sorted(steps))

    def test_te_sqrt_reads_only_its_input(self):
        self.assertEqual(set(re.findall(r"var:[a-z_]+", re.sub(r"#[^\n]*", "", _read(OUT)))), {"var:te_math_in"})


if __name__ == "__main__":
    unittest.main()
