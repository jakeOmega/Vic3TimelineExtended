# -*- coding: utf-8 -*-
"""The Map Room's color scales (common/script_values/te_journal_map_scales_generated.txt, gen_journal_map_scales.py).

A wrong segment paints a wrong color and the engine logs nothing, so the committed trees are parsed and evaluated
here, in floats and in the engine's five-decimal fixed point, against the generator's own knots; and the map reads
exactly the factors the generator writes, none by hand.
"""

import importlib.util
import math
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(REPO, "common", "script_values", "te_journal_map_scales_generated.txt")
HAND = os.path.join(REPO, "common", "script_values", "te_journal_map_values.txt")
ROOM = os.path.join(REPO, "common", "journal_entries", "te_journal_maps.txt")

_spec = importlib.util.spec_from_file_location(
    "gen_journal_map_scales", os.path.join(REPO, "scripts", "generators", "gen_journal_map_scales.py"))
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _parse(tokens, i):
    pairs = []
    while tokens[i] != "}":
        key, op = tokens[i], tokens[i + 1]
        if tokens[i + 2] == "{":
            value, i = _parse(tokens, i + 3)
        else:
            value, i = tokens[i + 2], i + 3
        pairs.append((key, value) if op == "=" else ("compare", (key, op, value)))
    return pairs, i + 1


def tree(text, name):
    tokens = re.findall(r"[{}]|[<>]=?|=|[^\s{}<>=]+", re.sub(r"#[^\n]*", "", text))
    start = next(i for i in range(len(tokens)) if tokens[i:i + 3] == [name, "=", "{"])
    return _parse(tokens, start + 3)[0]


def _cut(x):
    """The engine's fixed point: five decimals, toward zero."""
    return math.trunc(round(x * 100000, 6)) / 100000


OPS = {"value": lambda v, n: n, "add": lambda v, n: v + n, "subtract": lambda v, n: v - n,
       "multiply": lambda v, n: v * n, "divide": lambda v, n: v / n,
       "min": lambda v, n: max(v, n), "max": lambda v, n: min(v, n)}


def evaluate(block, x, inp, have=True, fixed=False, value=0.0):
    """A generated factor at input x: literals, the input token, has_variable (have), if / else_if / else."""
    def lit(t):
        return x if t == inp else float(t)

    def holds(limit):
        for key, arg in limit:
            if key == "has_variable":
                if not have:
                    return False
            else:
                a, op, b = arg
                if not {"<": lit(a) < lit(b), ">": lit(a) > lit(b)}[op]:
                    return False
        return True

    taken = False
    for key, arg in block:
        if key in ("if", "else_if", "else"):
            if key == "if":
                taken = False
            if taken:
                continue
            if key != "else" and not holds(dict(arg).get("limit", [])):
                continue
            taken = True
            value = evaluate([p for p in arg if p[0] != "limit"], x, inp, have, fixed, value)
        else:
            value = OPS[key](value, lit(arg))
            if fixed:
                value = _cut(value)
    return value


def reference(knots, x):
    """The curve through the knots, its end segments carried on, clamped to 0-1."""
    (a, fa), (b, fb) = (knots[0], knots[1]) if x < knots[1][0] else next(
        (p, q) for p, q in zip(knots, knots[1:]) if x < q[0] or q is knots[-1])
    return min(1.0, max(0.0, fa + (x - a) * (fb - fa) / (b - a)))


class ScalesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _read(OUT)

    def factor(self, scale, x, have=True, fixed=False):
        return evaluate(tree(self.text, f"te_jmap_{scale['name']}_factor"), x, scale["input"], have, fixed)

    def samples(self, scale):
        ks = [x for x, _ in scale["knots"]]
        lo, hi = ks[0], ks[-1]
        span = hi - lo
        xs = set(ks) | {lo - span / 2, hi + span / 2}
        xs |= {lo + span * i / 200 for i in range(201)}
        return sorted(xs)

    def test_the_committed_file_is_current(self):
        self.assertEqual(self.text, gen.render(), "run scripts/generators/gen_journal_map_scales.py")

    def test_one_bom(self):
        with open(OUT, "rb") as f:
            raw = f.read(6)
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))

    def test_each_tree_follows_its_knots(self):
        for scale in gen.SCALES:
            for fixed in (False, True):
                for x in self.samples(scale):
                    with self.subTest(map=scale["name"], x=x, fixed=fixed):
                        want = reference(scale["knots"], x)
                        self.assertAlmostEqual(self.factor(scale, x, fixed=fixed), want, delta=1e-4)

    def test_rising_from_0_to_1(self):
        for scale in gen.SCALES:
            ys = [self.factor(scale, x) for x in self.samples(scale)]
            with self.subTest(map=scale["name"]):
                self.assertEqual(ys, sorted(ys))
                self.assertEqual((ys[0], ys[-1]), (0.0, 1.0))

    def test_a_three_color_map_splits_at_its_midpoint(self):
        # map_color splits on factor < 0.5, so the midpoint knot (replacement, none, 100 men) must sit at 0.5 exactly
        for scale in gen.SCALES:
            if not scale["three"]:
                continue
            mids = [x for x, y in scale["knots"] if y == 0.5]
            with self.subTest(map=scale["name"]):
                self.assertEqual(len(mids), 1)
                self.assertEqual(self.factor(scale, mids[0], fixed=True), 0.5)
                name = f"te_jmap_{scale['name']}_factor"
                for half in ("lower", "upper"):
                    self.assertIn(f"{name}_{half} = {{", self.text)

    def test_a_figure_is_read_only_once_it_exists(self):
        # issue #1418: a has_variable in the same AND doesn't stop the read, so the read sits inside the guard's if
        for scale in gen.SCALES:
            body = tree(self.text, f"te_jmap_{scale['name']}_factor")
            with self.subTest(map=scale["name"]):
                if scale["guards"]:
                    self.assertEqual(self.factor(scale, 1e9, have=False), 0.0)
                    outer = [k for k, _ in body if k not in ("min", "max")]
                    self.assertEqual(outer, ["value", "if"], "a guarded factor is value = 0 and one guarded if")
                    for g in scale["guards"]:
                        self.assertIn(("has_variable", g), dict(dict(body)["if"])["limit"])
                else:
                    self.assertNotIn("var:", scale["input"])

    def test_a_soft_cap_runs_its_ratio_shallower_past_the_soft_bound(self):
        for scale in gen.SCALES:
            ks = scale["knots"]
            slopes = [(fb - fa) / (b - a) for (a, fa), (b, fb) in zip(ks, ks[1:])]
            with self.subTest(map=scale["name"]):
                if len(ks) == 3 and not scale["three"]:
                    self.assertAlmostEqual(slopes[0] / slopes[1], gen.SLOPE_RATIO)
                if len(ks) == 5:
                    self.assertAlmostEqual(slopes[1] / slopes[0], gen.SLOPE_RATIO)
                    self.assertAlmostEqual(slopes[2] / slopes[3], gen.SLOPE_RATIO)


class UseTest(unittest.TestCase):
    def test_the_map_reads_only_generated_factors(self):
        generated = set(re.findall(r"^(te_jmap_\w+)\s*=\s*\{", _read(OUT), re.M))
        used = set(re.findall(r"\b(te_jmap_\w+_factor(?:_lower|_upper)?)\b", _read(ROOM)))
        self.assertEqual(used - generated, set(), "factors the map reads that the generator doesn't write")
        top = {n for n in generated if not n.endswith(("_lower", "_upper"))}
        three = {f"te_jmap_{s['name']}_factor" for s in gen.SCALES if s["three"]}
        self.assertEqual(top - used, set(), "generated factors no map reads")
        self.assertEqual({n for n in used if n.endswith("_lower")}, {n + "_lower" for n in three})

    def test_no_factor_by_hand(self):
        # two top-level script values with one name across files: the engine keeps one and drops the other silently
        self.assertEqual(re.findall(r"^(te_jmap_\w+_factor\w*)\s*=", _read(HAND), re.M), [])

    def test_a_three_color_split_reads_the_factor(self):
        # a raw threshold beside the factor would put the midpoint in two places
        room = _read(ROOM)
        for scale in gen.SCALES:
            if scale["three"]:
                with self.subTest(map=scale["name"]):
                    self.assertIn(f"te_jmap_{scale['name']}_factor < 0.5", room)


if __name__ == "__main__":
    unittest.main()
