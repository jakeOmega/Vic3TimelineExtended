# -*- coding: utf-8 -*-
"""The Map Room's color scales (common/script_values/te_journal_map_scales_generated.txt) and the effects that fit them
to the world (common/scripted_effects/te_journal_map_ranges_generated.txt), both from gen_journal_map_scales.py.

A wrong segment paints a wrong color and the engine logs nothing, so the committed trees are parsed and evaluated
here, in floats and in the engine's five-decimal fixed point: a fixed map against its knots, a map fitted to the world
against the generator's own reference (world_factor) for several measured ranges, the unmeasured default among them.
The map reads exactly the factors the generator writes, none by hand; each fitted map is measured over the states it
paints, on a pick and each month.
"""

import importlib.util
import math
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(REPO, "common", "script_values", "te_journal_map_scales_generated.txt")
EFFECTS_OUT = os.path.join(REPO, "common", "scripted_effects", "te_journal_map_ranges_generated.txt")
HAND = os.path.join(REPO, "common", "script_values", "te_journal_map_values.txt")
ROOM = os.path.join(REPO, "common", "journal_entries", "te_journal_maps.txt")
MAP_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_journal_map_effects.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "te_journal_map_on_actions.txt")
# The systems' entries draw the Map Room's maps of their systems too (test_journal_map_modes.SYSTEM_MAPS).
ENTRIES = [os.path.join(REPO, "common", "journal_entries", f"{name}.txt") for name in (
    "je_global_warming", "je_nuclear_program", "je_covert_warfare", "je_united_nations", "je_cultural_hegemony",
    "je_grand_monuments", "je_colonial_empire")]

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


def trees(text):
    """{name: parsed body} for every top-level block."""
    tokens = re.findall(r"[{}]|[<>]=?|=|[^\s{}<>=]+", re.sub(r"#[^\n]*", "", text))
    out, i = {}, 0
    while i < len(tokens):
        name = tokens[i]
        body, i = _parse(tokens, i + 3)
        out[name] = body
    return out


def _cut(x):
    """The engine's fixed point: five decimals, toward zero."""
    return math.trunc(round(x * 100000, 6)) / 100000


OPS = {"value": lambda v, n: n, "add": lambda v, n: v + n, "subtract": lambda v, n: v - n,
       "multiply": lambda v, n: v * n, "divide": lambda v, n: v / n,
       "min": lambda v, n: max(v, n), "max": lambda v, n: min(v, n)}
CMP = {"<": lambda a, b: a < b, ">": lambda a, b: a > b, "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b}


class Env:
    """A paint's view: the state's figure (x, for the map's input token), whether its guards hold (have), and the
    globals the range effects stored (globals: name -> value)."""

    def __init__(self, defs, inp, x, have=True, globs=None, fixed=False):
        self.defs, self.inp, self.x, self.have, self.globs, self.fixed = defs, inp, x, have, globs or {}, fixed

    def lit(self, t):
        if t == self.inp:
            return self.x
        if t.startswith("global_var:"):
            return self.globs[t.split(":", 1)[1]]
        if t in self.defs:
            return self.run(self.defs[t])
        return float(t)

    def holds(self, limit):
        for key, arg in limit:
            if key == "has_variable":
                if not self.have:
                    return False
            elif key == "has_global_variable":
                if arg not in self.globs:
                    return False
            else:
                a, op, b = arg
                if not CMP[op](self.lit(a), self.lit(b)):
                    return False
        return True

    def run(self, block, value=0.0):
        taken = False
        for key, arg in block:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    taken = False
                if taken:
                    continue
                if key != "else" and not self.holds(dict(arg).get("limit", [])):
                    continue
                taken = True
                value = self.run([p for p in arg if p[0] != "limit"], value)
            else:
                value = OPS[key](value, self.lit(arg))
                if self.fixed:
                    value = _cut(value)
        return value


def reference(knots, x):
    """The curve through the knots, its end segments carried on, clamped to 0-1."""
    (a, fa), (b, fb) = (knots[0], knots[1]) if x < knots[1][0] else next(
        (p, q) for p, q in zip(knots, knots[1:]) if x < q[0] or q is knots[-1])
    return min(1.0, max(0.0, fa + (x - a) * (fb - fa) / (b - a)))


FIXED = [s for s in gen.SCALES if not gen.fitted(s)]
FITTED = [s for s in gen.SCALES if gen.fitted(s)]


def ranges(scale):
    """Measured ranges to try (None: not yet measured): the default, a narrow and a wide one, one narrower than the
    map's min_span, and for a map with a meaningful midpoint a world wholly on each side of it."""
    w = scale["world"]
    lo, hi = w["default"]
    span = hi - lo
    out = [None, (lo, hi), (lo + span * 0.25, lo + span * 0.6), (lo - span * 0.5, hi + span), (lo, lo)]
    if w["kind"] == "doubling":
        out = [None, (lo, hi), (lo * 4, lo * 64), (0.002, hi * 8), (lo, lo * 1.5)]
    if w["kind"] == "mid":
        m = w["mid"]
        out += [(m + span * 0.1, m + span * 0.4), (m - span * 0.4, m - span * 0.1)]
    return out


def samples(scale, rng):
    L, H = gen.world_bounds(scale, *(rng or (None, None)))
    span = H - L
    xs = {L - span / 2, H + span / 2} | {L + span * i / 100 for i in range(101)}
    if scale["world"]["kind"] == "mid":
        m = scale["world"]["mid"]
        xs |= {m, m - 1e-3, m + 1e-3, m - scale["world"]["min_half"]}
    if scale["world"]["kind"] == "doubling":
        xs = {x for x in xs if x > 0} | {L * 2 ** k for k in range(12)} | {0.0}
    return sorted(xs)


def store(scale, rng):
    n = gen.range_name(scale)
    return {} if rng is None else {f"te_jmap_rng_{n}_lo": rng[0], f"te_jmap_rng_{n}_hi": rng[1]}


class ScalesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _read(OUT)
        cls.defs = trees(cls.text)

    def factor(self, scale, x, have=True, globs=None, fixed=False):
        env = Env(self.defs, scale["input"], x, have, globs, fixed)
        return env.run(self.defs[f"te_jmap_{scale['name']}_factor"])

    def test_the_committed_files_are_current(self):
        self.assertEqual(self.text, gen.render(), "run scripts/generators/gen_journal_map_scales.py")
        self.assertEqual(_read(EFFECTS_OUT), gen.render_effects(), "run scripts/generators/gen_journal_map_scales.py")

    def test_one_bom(self):
        for path in (OUT, EFFECTS_OUT):
            with open(path, "rb") as f:
                raw = f.read(6)
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), path)
            self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"), path)

    def test_nearly_every_map_is_fitted_to_the_world(self):
        # owner, 2026-11-07: the regional differences, not the world's level. Only the agent networks (their tiers),
        # the paleness of the leading cause and of Ownership's leading holder (a share on a categorical map) and City
        # Rank (a rank is already a place in the world, and its first 20 are tourism's Cities bonus) keep fixed curves.
        self.assertEqual({s["name"] for s in FIXED}, {"net", "cause", "own", "city_top", "city_rest"})

    def test_each_fixed_tree_follows_its_knots(self):
        for scale in FIXED:
            ks = [x for x, _ in scale["knots"]]
            lo, hi = ks[0], ks[-1]
            xs = sorted(set(ks) | {lo - (hi - lo) / 2, hi + (hi - lo) / 2} |
                        {lo + (hi - lo) * i / 200 for i in range(201)})
            for fixed in (False, True):
                for x in xs:
                    with self.subTest(map=scale["name"], x=x, fixed=fixed):
                        self.assertAlmostEqual(self.factor(scale, x, fixed=fixed), reference(scale["knots"], x),
                                               delta=1e-4)

    def test_each_fitted_tree_follows_the_world(self):
        # against the generator's reference, the same curve in Python, for each measured range; the fixed point's
        # five decimals cost a little on a narrow span
        for scale in FITTED:
            for rng in ranges(scale):
                globs = store(scale, rng)
                for x in samples(scale, rng):
                    want = gen.world_factor(scale, *(rng or (None, None)), x)
                    for fixed, delta in ((False, 1e-4), (True, 5e-3)):
                        with self.subTest(map=scale["name"], range=rng, x=x, fixed=fixed):
                            self.assertAlmostEqual(self.factor(scale, x, globs=globs, fixed=fixed), want, delta=delta)

    def test_the_colors_span_the_world_s_range(self):
        # the world's high takes the whole color; its low none, or the neutral middle where the whole world sits on
        # one side of a meaningful midpoint
        for scale in FITTED:
            w = scale["world"]
            for rng in ranges(scale):
                L, H = gen.world_bounds(scale, *(rng or (None, None)))
                ys = [gen.world_factor(scale, *(rng or (None, None)), x) for x in samples(scale, rng)]
                with self.subTest(map=scale["name"], range=rng):
                    self.assertEqual(ys, sorted(ys), "rising")
                    high = gen.world_factor(scale, *(rng or (None, None)), H)
                    low = gen.world_factor(scale, *(rng or (None, None)), L)
                    if w["kind"] == "mid" and H <= w["mid"]:
                        self.assertEqual((round(low, 9), round(high, 9)), (0.0, 0.5))
                    elif w["kind"] == "mid" and L >= w["mid"]:
                        self.assertEqual((round(low, 9), round(high, 9)), (0.5, 1.0))
                    else:
                        self.assertEqual((round(low, 9), round(high, 9)), (0.0, 1.0))
                    # rounded: 0.5 - 0.4 is 0.0999... in floats
                    self.assertGreaterEqual(round(H - L, 9), scale["min_span"] if w["kind"] != "doubling" else 0)

    def test_a_three_color_map_splits_at_its_midpoint(self):
        # map_color splits on factor < 0.5: a meaningful midpoint (replacement, none, 100 men) is at 0.5 wherever the
        # world lies on both sides of it, and a map with none splits at its range's middle
        for scale in FITTED:
            if not scale["three"]:
                continue
            w = scale["world"]
            name = f"te_jmap_{scale['name']}_factor"
            with self.subTest(map=scale["name"]):
                for half in ("lower", "upper"):
                    self.assertIn(f"{name}_{half} = {{", self.text)
                for rng in ranges(scale):
                    L, H = gen.world_bounds(scale, *(rng or (None, None)))
                    globs = store(scale, rng)
                    if w["kind"] == "mid":
                        if L < w["mid"] < H:
                            self.assertEqual(self.factor(scale, w["mid"], globs=globs, fixed=True), 0.5)
                    else:
                        self.assertAlmostEqual(self.factor(scale, (L + H) / 2, globs=globs, fixed=True), 0.5,
                                               delta=1e-3)
        mids = {s["name"] for s in FITTED if s["world"]["kind"] == "mid"}
        self.assertEqual(mids, {"wc", "tfr", "natural", "sex", "mig", "comfort_base", "comfort", "growth"})

    def test_a_figure_is_read_only_once_it_exists(self):
        # issue #1418: a has_variable in the same AND doesn't stop the read, so the read sits inside the guard's if
        for scale in gen.SCALES:
            body = self.defs[f"te_jmap_{scale['name']}_factor"]
            with self.subTest(map=scale["name"]):
                if scale["guards"]:
                    globs = store(scale, None) if gen.fitted(scale) else None
                    self.assertEqual(self.factor(scale, 1e9, have=False, globs=globs), 0.0)
                    outer = [k for k, _ in body if k not in ("min", "max")]
                    self.assertEqual(outer, ["value", "if"], "a guarded factor is value = 0 and one guarded if")
                    for g in scale["guards"]:
                        self.assertIn(("has_variable", g), dict(dict(body)["if"])["limit"])
                else:
                    self.assertNotIn("var:", scale["input"])

    def test_a_soft_cap_runs_its_ratio_shallower_past_the_soft_bound(self):
        for scale in gen.SCALES:
            ks = scale["knots"] if not gen.fitted(scale) else scale["world"].get("knots")
            if not ks:
                continue
            slopes = [(fb - fa) / (b - a) for (a, fa), (b, fb) in zip(ks, ks[1:])]
            with self.subTest(map=scale["name"]):
                if len(ks) == 3 and not scale["three"]:
                    self.assertAlmostEqual(slopes[0] / slopes[1], gen.SLOPE_RATIO)

    def test_a_doubling_scale_gives_each_doubling_the_same_color(self):
        doubled = [s for s in FITTED if s["world"]["kind"] == "doubling"]
        self.assertEqual([s["name"] for s in doubled], ["gdppc", "soldiers", "hq", "war_dead", "trade"])
        for scale in doubled:
            floor = scale["world"]["floor"]
            for lo, hi in ((floor * 50, floor * 6400), (floor * 200, floor * 4000)):
                L, H = gen.world_bounds(scale, lo, hi)
                steps = gen.log2_pieces(H / L)
                ys = [gen.world_factor(scale, lo, hi, L * 2 ** k) for k in range(int(steps) + 1)]
                with self.subTest(map=scale["name"], range=(lo, hi)):
                    for a, b in zip(ys, ys[1:]):
                        self.assertAlmostEqual(b - a, 1 / steps)
        with self.assertRaises(ValueError):
            gen.doubling(0.25, 100)

    def test_the_low_and_high_never_meet(self):
        # a span floor in every fitted map (or a ratio floor for a doubling): no division by nothing
        for scale in FITTED:
            n = gen.range_name(scale)
            for rng in ((5, 5), (5, 4)):
                lo = Env(self.defs, scale["input"], 0, globs=store(scale, rng)).lit(f"te_jmap_{n}_lo")
                hi = Env(self.defs, scale["input"], 0, globs=store(scale, rng)).lit(f"te_jmap_{n}_hi")
                with self.subTest(map=scale["name"], range=rng):
                    self.assertGreater(hi, lo)


class RangesTest(unittest.TestCase):
    """te_journal_map_ranges_generated.txt: each fitted map is measured over the states it paints, on a pick and each
    month."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(EFFECTS_OUT)
        cls.defs = trees(cls.text)

    def test_each_range_trims_both_ends_and_falls_back_to_the_extremes(self):
        for scale in FITTED:
            n = gen.range_name(scale)
            body = self.text[self.text.index(f"te_jmap_range_{n} = {{"):]
            body = body[:body.index("\n}\n")]
            with self.subTest(map=scale["name"]):
                self.assertEqual(body.count(f"position = {gen.TRIM}"), 2)
                self.assertEqual(body.count("position = 0"), 2)
                self.assertEqual(body.count(f"order_by = te_jmap_{n}_input\n"), 2)
                self.assertEqual(body.count(f"order_by = te_jmap_{n}_input_neg"), 2)
                self.assertIn(f"remove_global_variable = te_jmap_rng_{n}_lo", body)
                self.assertIn(f"remove_global_variable = te_jmap_rng_{n}_hi", body)

    def test_each_range_measures_the_states_the_map_paints(self):
        # the range's states are the map's: the Map Room's branch conditions for the selector, without the selector and
        # the three-color split. Emissions paints through shared triggers (te_jmap_gw_no_data, te_jmap_gw_removal:
        # a removal is green, apart from the scale), and GDP per capita leaves out a state with none (a doubling has
        # no zero). Armed Forces, Company Headquarters and War Dead paint a zero (or a loss) apart from the scale too,
        # in branches of their own, so their lerp's conditions are still their range's.
        room = _read(ROOM)
        mc = room[room.index("map_color = {"):room.index("map_color_second = {")]
        for scale in FITTED:
            if scale.get("range_of") or scale["name"] in ("gw", "gdppc"):
                continue
            pattern = (r"limit = \{\s*te_jmap_selector = " + str(scale["sel"]) + r"\b([^{}]*)\}\s*lerp = \{[^{}]*factor ="
                       r" te_jmap_" + scale["name"] + r"_factor")
            m = re.search(pattern, mc)
            with self.subTest(map=scale["name"]):
                self.assertIsNotNone(m, "no lerp branch")
                cond = re.sub(r"te_jmap_\w+_factor < 0\.5", "", m.group(1))
                self.assertEqual(" ".join(cond.split()), " ".join(scale["where"]))

    def test_every_fitted_pick_is_measured(self):
        body = self.text[self.text.index("te_jmap_refresh_range = {"):]
        picked = {int(sel): name for sel, name in
                  re.findall(r"limit = \{ te_jmap_selector = (\d+) \}\s*(te_jmap_range_\w+) = yes", body)}
        self.assertEqual(picked, {s["sel"]: f"te_jmap_range_{gen.range_name(s)}" for s in FITTED})
        self.assertEqual([k for k, _ in self.defs["te_jmap_refresh_entry_ranges"]],
                         ["te_jmap_range_gw", "te_jmap_range_gm"])

    def test_a_pick_and_the_month_measure(self):
        effects = _read(MAP_EFFECTS)
        setter = effects[effects.index("te_jmap_set_selector = {"):]
        setter = setter[:setter.index("\n}\n")]
        self.assertLess(setter.index("set_global_variable = { name = te_jmap_sel"),
                        setter.index("te_jmap_refresh_range = yes"))
        on_actions = _read(ON_ACTIONS)
        self.assertRegex(on_actions, r"on_monthly_pulse = \{\s*on_actions = \{\s*te_jmap_monthly_ranges")
        monthly = on_actions[on_actions.index("te_jmap_monthly_ranges = {"):]
        self.assertIn("te_jmap_refresh_range = yes", monthly)
        self.assertIn("te_jmap_refresh_entry_ranges = yes", monthly)

    def test_the_pick_tooltips_give_the_world_s_range(self):
        # the map has no legend: each fitted pick's tooltip prints the range it is painted on now
        loc = "".join(_read(os.path.join(REPO, "localization", "english", f)) for f in
                      os.listdir(os.path.join(REPO, "localization", "english")) if f.endswith(".yml"))
        sguis = _read(os.path.join(REPO, "common", "scripted_guis", "te_journal_map_sguis.txt"))
        for scale in FITTED:
            m = re.search(r"^(te_jmap_pick_\w+)_sgui = \{(?:(?!^\}).)*?SEL = " + str(scale["sel"]) + r"\b", sguis,
                          re.M | re.S)
            self.assertIsNotNone(m, scale["name"])
            line = re.search(r"^ " + m.group(1) + r'_desc:0 "(.*)"$', loc, re.M)
            n = scale["name"]
            with self.subTest(map=n):
                self.assertIsNotNone(line)
                self.assertIn(f"ScriptValue('te_jmap_{n}_lo')", line.group(1))
                self.assertIn(f"ScriptValue('te_jmap_{n}_hi')", line.group(1))


class UseTest(unittest.TestCase):
    def test_the_map_reads_only_generated_factors(self):
        generated = set(re.findall(r"^(te_jmap_\w+)\s*=\s*\{", _read(OUT), re.M))
        used = set(re.findall(r"\b(te_jmap_\w+_factor(?:_lower|_upper)?)\b", _read(ROOM)))
        self.assertEqual(used - generated, set(), "factors the map reads that the generator doesn't write")
        for path in ENTRIES:
            mine = set(re.findall(r"\b(te_jmap_\w+_factor(?:_lower|_upper)?)\b", _read(path)))
            self.assertEqual(mine - generated, set(), f"{os.path.basename(path)}: factors no generator writes")
        top = {n for n in generated if n.endswith("_factor")}
        three = {f"te_jmap_{s['name']}_factor" for s in gen.SCALES if s["three"]}
        self.assertEqual(top - used, set(), "generated factors no map reads")
        self.assertEqual({n for n in used if n.endswith("_lower")}, {n + "_lower" for n in three})

    def test_no_generated_value_by_hand(self):
        # two top-level script values with one name across files: the engine keeps one and drops the other silently
        generated = set(re.findall(r"^(te_jmap_\w+)\s*=\s*\{", _read(OUT), re.M))
        hand = set(re.findall(r"^(te_jmap_\w+)\s*=", _read(HAND), re.M))
        self.assertEqual(generated & hand, set())

    def test_a_three_color_split_reads_the_factor(self):
        # a raw threshold beside the factor would put the midpoint in two places
        room = _read(ROOM)
        for scale in gen.SCALES:
            if scale["three"]:
                with self.subTest(map=scale["name"]):
                    self.assertIn(f"te_jmap_{scale['name']}_factor < 0.5", room)


if __name__ == "__main__":
    unittest.main()
