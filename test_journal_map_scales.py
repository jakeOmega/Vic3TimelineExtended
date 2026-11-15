# -*- coding: utf-8 -*-
"""The Map Room's color scales (common/script_values/te_journal_map_scales_generated.txt) and the effects that fit them
to the world (common/scripted_effects/te_journal_map_ranges_generated.txt), both from gen_journal_map_scales.py.

A wrong segment paints a wrong color and the engine logs nothing, so the committed trees are parsed and evaluated
here, in floats and in the engine's five-decimal fixed point: a fixed map against its knots, a map fitted to the world
against the generator's own reference (world_factor) for several measured ranges, the unmeasured default among them.
The map reads exactly the factors the generator writes, none by hand; each fitted map is measured over the states it
paints, on a pick and each month.

The Map Room's options (2026-11-14) live in the same two files: a range the Map Room reads counts and orders only the
states in its area and leaves out the trim its Outliers option gives, never past the middle of a short list. The
range effects are run here over made-up states (RangeRunTest), the way the engine would run them, against a plain
sort; a map a system's own entry draws too keeps a range the options don't touch.

The Scale option (the thirteenth pass) is a branch inside each factor the Map Room reads: every committed tree is
evaluated under Linear and Logarithmic against the generator's reference (ScaleTest), and the effects that store a
Ranked map's places are run over made-up states, ties and all, against a plain sort (RankRunTest).
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
ROOM_FILE = os.path.join(REPO, "common", "journal_entries", "te_journal_maps.txt")
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
    """A paint's view: the state's figure (x, for the map's input token; a dict by token where several maps'
    figures are in play), whether its guards hold (have; absent names the state variables it lacks whatever have
    says), the globals the range effects stored (globals: name -> value), and the hand-written script values and
    state variables a generated value reads (named: te_jmap_selector, te_jmap_area, te_jmap_trim, te_jmap_scale,
    var:te_jmap_rank). The Scale option is the map's own curve unless named says otherwise."""

    def __init__(self, defs, inp, x, have=True, globs=None, fixed=False, named=None, absent=()):
        self.defs, self.inp, self.x, self.have, self.globs, self.fixed = defs, inp, x, have, globs or {}, fixed
        self.named = {"te_jmap_scale": 0, **(named or {})}
        self.absent = set(absent)

    def lit(self, t):
        if t == self.inp or (isinstance(self.inp, (set, frozenset)) and t in self.inp):
            return self.x[t] if isinstance(self.x, dict) else self.x
        if t in self.named:
            return self.named[t]
        if t.startswith("global_var:"):
            return self.globs[t.split(":", 1)[1]]
        if t in self.defs:
            return self.run(self.defs[t])
        return float(t)

    def holds(self, limit):
        for key, arg in limit:
            if key == "has_variable":
                if not self.have or arg in self.absent:
                    return False
            elif key == "has_global_variable":
                if arg not in self.globs:
                    return False
            elif key == "OR":
                if not any(self.holds([child]) for child in arg):
                    return False
            elif key == "compare":
                a, op, b = arg
                if not CMP[op](self.lit(a), self.lit(b)):
                    return False
            elif self.lit(key) != self.lit(arg):    # name = number
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
            elif key == "floor":
                # the engine's floor, on its fixed point: a hair under a whole number is that number less one
                value = float(math.floor(_cut(value)))
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

    def factor(self, scale, x, have=True, globs=None, fixed=False, option=0, rank=None):
        """The committed tree's factor at x, under a Scale setting (the map's own curve by default) and, for
        Ranked, with the state's stored place (None: it has none)."""
        named = {"te_jmap_scale": option}
        if rank is not None:
            named["var:te_jmap_rank"] = rank
        env = Env(self.defs, scale["input"], x, have, globs, fixed, named,
                  absent=() if rank is not None else ("te_jmap_rank",))
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
        self.assertEqual([s["name"] for s in doubled], ["gdppc", "soldiers", "hq", "war_dead", "trade", "invest"])
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


def effect_body(text, name):
    """The text of one top-level effect, its name line to its closing brace."""
    body = text[text.index(f"\n{name} = {{") + 1:]
    return body[:body.index("\n}\n") + 2]


ROOM = [s for s in FITTED if gen.in_room(s)]
ENTRY = [s for s in FITTED if not gen.in_room(s)]
OWN = [s for s in FITTED if gen.range_name(s) == s["name"]]


class RangesTest(unittest.TestCase):
    """te_journal_map_ranges_generated.txt: each fitted map is measured over the states it paints, on a pick and each
    month; the Map Room's ranges over its area and on its trim, the entries' over the world on the default."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(EFFECTS_OUT)
        cls.defs = trees(cls.text)

    def test_each_range_counts_its_states_then_takes_both_ends_at_the_trim(self):
        for scale in OWN:
            n = scale["name"]
            body, ends = effect_body(self.text, f"te_jmap_range_{n}"), effect_body(self.text, f"te_jmap_measure_{n}")
            limit = " ".join(gen.measured(scale))
            with self.subTest(map=n):
                self.assertIn(f"remove_global_variable = te_jmap_rng_{n}_lo", body)
                self.assertIn(f"remove_global_variable = te_jmap_rng_{n}_hi", body)
                # the count, over the very states the two orderings take: a trim worked out from another list could
                # pass the end of this one, and a position past the end takes the last state instead of none
                count = body[body.index("every_state = {"):]
                self.assertIn(f"limit = {{ {limit} }}\n\t\tchange_global_variable = {{ name = te_jmap_n add = 1 }}",
                              count)
                self.assertEqual(ends.count(f"limit = {{ {limit} }}"), 2)
                self.assertLess(body.index("set_global_variable = { name = te_jmap_n value = 0 }"),
                                body.index("every_state = {"))
                trim = "te_jmap_trim_count" if gen.in_room(scale) else "te_jmap_trim_count_entry"
                self.assertLess(body.index("every_state = {"),
                                body.index(f"set_global_variable = {{ name = te_jmap_k value = {trim} }}"))
                self.assertLess(body.index("name = te_jmap_k value"), body.index(f"te_jmap_measure_at = {{ MAP = {n} }}"))
                # a literal position, the argument: position takes no script value
                self.assertEqual(ends.count("position = $K$"), 2)
                self.assertNotRegex(body, r"\bposition\s*=")
                self.assertEqual(ends.count(f"order_by = te_jmap_{n}_input\n"), 1)
                self.assertEqual(ends.count(f"order_by = te_jmap_{n}_input_neg\n"), 1)
                # the highest by the figure, the lowest by its negative, each storing the figure itself
                top, bottom = ends.split("ordered_state = {")[1:]
                self.assertIn(f"order_by = te_jmap_{n}_input\n", top)
                self.assertIn(f"name = te_jmap_rng_{n}_hi value = te_jmap_{n}_input }}", top)
                self.assertIn(f"order_by = te_jmap_{n}_input_neg\n", bottom)
                self.assertIn(f"name = te_jmap_rng_{n}_lo value = te_jmap_{n}_input }}", bottom)

    def test_the_ladder_holds_a_literal_position_for_every_trim(self):
        # te_jmap_measure_at: K = 0 .. TRIM_MAX, each taken while the trim is below the next whole number, and
        # nothing at all where no state has a figure
        ladder = effect_body(self.text, "te_jmap_measure_at")
        calls = re.findall(r"(?:limit = \{ te_jmap_cut < (\d+) \}|else = \{)\s*te_jmap_measure_\$MAP\$ = \{ K = (\d+) \}",
                           ladder)
        self.assertEqual([int(k) for _lt, k in calls], list(range(gen.TRIM_MAX + 1)))
        self.assertEqual([int(lt) for lt, _k in calls[:-1]], list(range(1, gen.TRIM_MAX + 1)))
        self.assertEqual(calls[-1][0], "", "the last position takes every larger trim")
        self.assertRegex(ladder, r"^te_jmap_measure_at = \{\n\tif = \{\n\t\tlimit = \{ te_jmap_states > 0 \}")
        self.assertGreaterEqual(gen.TRIM_MAX, gen.TRIM)

    def test_each_range_measures_the_states_the_map_paints(self):
        # the range's states are the map's: the Map Room's branch conditions for the selector, without the selector and
        # the three-color split. Emissions paints through shared triggers (te_jmap_gw_no_data, te_jmap_gw_removal:
        # a removal is green, apart from the scale), and GDP per capita leaves out a state with none (a doubling has
        # no zero). Armed Forces, Company Headquarters and War Dead paint a zero (or a loss) apart from the scale too,
        # in branches of their own, so their lerp's conditions are still their range's.
        room = _read(ROOM_FILE)
        mc = room[room.index("map_color = {"):room.index("map_color_second = {")]
        for scale in ROOM:
            if scale.get("range_of") or scale["name"] in ("gw_room", "gdppc"):
                continue
            pattern = (r"limit = \{\s*te_jmap_selector = " + str(scale["sel"]) + r"\b([^{}]*)\}\s*lerp = \{[^{}]*factor ="
                       r" te_jmap_" + scale["name"] + r"_factor")
            m = re.search(pattern, mc)
            with self.subTest(map=scale["name"]):
                self.assertIsNotNone(m, "no lerp branch")
                cond = re.sub(r"te_jmap_\w+_factor < 0\.5", "", m.group(1))
                self.assertEqual(" ".join(cond.split()), " ".join(scale["where"]))

    def test_the_map_room_s_ranges_keep_to_its_area_and_the_entries_to_the_world(self):
        # the Area option: every range the Map Room reads counts and orders only the states in its area; a range a
        # system's own entry reads never asks, and takes the default trim, so limiting the Map Room to Europe leaves
        # Global Warming's and Grand Monuments' own pages as they were
        self.assertEqual(sorted(s["name"] for s in ENTRY), ["gm", "gw"])
        for scale in OWN:
            n = scale["name"]
            both = effect_body(self.text, f"te_jmap_range_{n}") + effect_body(self.text, f"te_jmap_measure_{n}")
            with self.subTest(map=n):
                if gen.in_room(scale):
                    self.assertEqual(both.count("te_jmap_in_area = yes"), 3, "the count and both orderings")
                    self.assertIn("value = te_jmap_trim_count }", both)
                    self.assertIn("set_global_variable = { name = te_jmap_shown_n value = te_jmap_states }", both)
                    self.assertIn("set_global_variable = { name = te_jmap_shown_k value = te_jmap_cut }", both)
                else:
                    self.assertNotIn("te_jmap_in_area", both)
                    self.assertNotIn("te_jmap_out", both)
                    self.assertIn("value = te_jmap_trim_count_entry }", both)
                    self.assertNotIn("te_jmap_shown_", both, "the page's figures are the Map Room's ranges' only")
        self.assertEqual(gen.measured(next(s for s in SCALES_BY_NAME["gw_room"])),
                         next(s for s in SCALES_BY_NAME["gw"])["where"] + ["te_jmap_in_area = yes"])

    def test_every_fitted_pick_is_measured(self):
        body = self.text[self.text.index("te_jmap_refresh_range = {"):]
        picked = {int(sel): name for sel, name in
                  re.findall(r"limit = \{ te_jmap_selector = (\d+) \}\s*(te_jmap_range_\w+) = yes", body)}
        self.assertEqual(picked, {s["sel"]: f"te_jmap_range_{gen.range_name(s)}" for s in ROOM})
        # the Map Room's Emissions and Grandeur measure their own ranges, not the entries'
        self.assertEqual((picked[18], picked[24]), ("te_jmap_range_gw_room", "te_jmap_range_gm_room"))
        self.assertEqual([k for k, _ in self.defs["te_jmap_refresh_entry_ranges"]],
                         ["te_jmap_range_gw", "te_jmap_range_gm"])

    def test_a_pick_an_option_and_the_month_measure(self):
        effects = _read(MAP_EFFECTS)
        setter = effect_body(effects, "te_jmap_set_selector")
        self.assertLess(setter.index("set_global_variable = { name = te_jmap_sel"),
                        setter.index("te_jmap_refresh_range = yes"))
        # the area's marks before the range that leaves the marked states out, and the viewer before the marks,
        # which are drawn around it
        for name in ("te_jmap_set_selector", "te_jmap_apply_options"):
            body = effect_body(effects, name)
            with self.subTest(effect=name):
                self.assertLess(body.index("te_jmap_note_viewer = yes"), body.index("te_jmap_mark_area = yes"))
                self.assertLess(body.index("te_jmap_mark_area = yes"), body.index("te_jmap_refresh_range = yes"))
        for name in ("te_jmap_set_area", "te_jmap_set_continent", "te_jmap_set_trim"):
            self.assertIn("te_jmap_apply_options = yes", effect_body(effects, name), name)
        on_actions = _read(ON_ACTIONS)
        self.assertRegex(on_actions, r"on_monthly_pulse = \{\s*on_actions = \{\s*te_jmap_monthly_ranges")
        monthly = on_actions[on_actions.index("te_jmap_monthly_ranges = {"):]
        self.assertIn("te_jmap_refresh_range = yes", monthly)
        self.assertIn("te_jmap_refresh_entry_ranges = yes", monthly)
        self.assertLess(monthly.index("te_jmap_mark_area = yes"), monthly.index("te_jmap_refresh_range = yes"))

    def test_the_pick_tooltips_give_the_range_and_what_it_was_measured_over(self):
        # the map has no legend: each fitted pick's tooltip prints the range it is painted on now (the Map Room's own
        # for Emissions and Grandeur), the area it runs over and what its ends leave out
        loc = "".join(_read(os.path.join(REPO, "localization", "english", f)) for f in
                      os.listdir(os.path.join(REPO, "localization", "english")) if f.endswith(".yml"))
        sguis = _read(os.path.join(REPO, "common", "scripted_guis", "te_journal_map_sguis.txt"))
        for scale in ROOM:
            m = re.search(r"^(te_jmap_pick_\w+)_sgui = \{(?:(?!^\}).)*?SEL = " + str(scale["sel"]) + r"\b", sguis,
                          re.M | re.S)
            self.assertIsNotNone(m, scale["name"])
            line = re.search(r"^ " + m.group(1) + r'_desc:0 "(.*)"$', loc, re.M)
            n = scale["name"]
            with self.subTest(map=n):
                self.assertIsNotNone(line)
                self.assertIn(f"ScriptValue('te_jmap_{n}_lo')", line.group(1))
                self.assertIn(f"ScriptValue('te_jmap_{n}_hi')", line.group(1))
                # the range's line is the tooltip's second, and ends on what the range leaves out
                self.assertTrue(line.group(1).split("\\n")[1].endswith("$te_jmap_measured_trim$"),
                                "what the range leaves out")
                self.assertNotRegex(line.group(1), r"\bthe world as it is now|the world's extreme now",
                                    "the area is the Map Room's, which may not be the world")
                if n != "comfort":    # Current Comfort's range is Base Comfort's, which says so
                    self.assertIn("$te_jmap_measured_area$", line.group(1))
        for key, custom in (("te_jmap_measured_area", "te_jmap_area_text"), ("te_jmap_measured_trim", "te_jmap_trim_text")):
            self.assertRegex(loc, rf'(?m)^ {key}:0 "\[GetPlayer\.GetCustom\(\'{custom}\'\)\]"$')


SCALES_BY_NAME = {}
for _s in gen.SCALES:
    SCALES_BY_NAME.setdefault(_s["name"], []).append(_s)


class OptionsTest(unittest.TestCase):
    """The script values the Map Room's options act through (te_journal_map_scales_generated.txt's tail)."""

    @classmethod
    def setUpClass(cls):
        cls.defs = trees(_read(OUT))

    def value(self, name, n=None, option=0, area=0, sel=0):
        globs = {} if n is None else {"te_jmap_n": n}
        env = Env(self.defs, None, 0, globs=globs, fixed=True,
                  named={"te_jmap_trim": option, "te_jmap_area": area, "te_jmap_selector": sel})
        return env.run(self.defs[name])

    def test_the_trim_follows_the_option_and_the_count(self):
        # the generator's reference, for every count a game can reach and each setting, under the world and under a
        # limited area
        for option in (gen.TRIM_DEFAULT, gen.TRIM_NONE, gen.TRIM_PERCENT):
            for area in (0, 1, 4):
                for n in list(range(0, 130)) + [199, 200, 399, 400, 1000, 1599, 1600, 1601, 2500]:
                    with self.subTest(option=option, area=area, n=n):
                        self.assertEqual(self.value("te_jmap_trim_count", n, option, area),
                                         gen.trim_count(n, option, limited=area > 0))

    def test_the_default_under_the_world_is_what_it_was(self):
        # before the options every range took position = TRIM: the fifth highest and the fifth lowest. Still so from
        # ten states with a figure up; below that the old position passed the middle of the list (or its end), so
        # now the ends close in instead
        for n in (10, 11, 40, 700, 3000):
            self.assertEqual(gen.trim_count(n), gen.TRIM, n)
            self.assertEqual(self.value("te_jmap_trim_count_entry", n), gen.TRIM, n)
        self.assertEqual([gen.trim_count(n) for n in range(10)], [0, 0, 0, 0, 1, 1, 2, 2, 3, 3])
        for n in range(0, 60):
            self.assertEqual(self.value("te_jmap_trim_count_entry", n), gen.trim_count(n), n)

    def test_the_other_settings(self):
        self.assertEqual([gen.trim_count(n, gen.TRIM_NONE) for n in (0, 5, 5000)], [0, 0, 0])
        # a twentieth, rounded down; the ladder's last position past 1,600 states
        self.assertEqual([gen.trim_count(n, gen.TRIM_PERCENT) for n in (19, 20, 39, 40, 1000, 1600, 5000)],
                         [0, 1, 1, 2, 50, gen.TRIM_MAX, gen.TRIM_MAX])
        # a limited area's default: a tenth of its states at most, so a country of fifteen keeps thirteen in range
        self.assertEqual([gen.trim_count(n, limited=True) for n in (9, 10, 15, 20, 39, 40, 400)], [0, 1, 1, 2, 3, 4, 4])

    def test_no_trim_passes_the_middle(self):
        # two states are always left to span: the kth highest is above the kth lowest
        for option in (gen.TRIM_DEFAULT, gen.TRIM_NONE, gen.TRIM_PERCENT):
            for limited in (False, True):
                for n in range(2, 400):
                    k = gen.trim_count(n, option, limited)
                    self.assertLess(k, n - 1 - k, (option, limited, n))
        self.assertEqual((gen.trim_count(0), gen.trim_count(1)), (0, 0))

    def test_the_pick_is_fitted_only_on_a_map_with_a_range(self):
        fitted = {s["sel"] for s in ROOM}
        self.assertEqual(len(fitted), 35)
        for sel in range(0, 60):
            self.assertEqual(self.value("te_jmap_pick_fitted", sel=sel), 1 if sel in fitted else 0, sel)
        # the categorical maps and the fixed scales: nothing to trim
        for sel in (0, 2, 11, 19, 20, 21, 22, 23, 25, 31, 32, 36):
            self.assertNotIn(sel, fitted)

    def test_the_page_reads_what_the_pick_was_measured_over(self):
        env = Env(self.defs, None, 0, globs={"te_jmap_shown_n": 212, "te_jmap_shown_k": 4, "te_jmap_n": 9, "te_jmap_k": 3})
        self.assertEqual((env.lit("te_jmap_shown_states"), env.lit("te_jmap_shown_cut")), (212, 4))
        self.assertEqual((env.lit("te_jmap_states"), env.lit("te_jmap_cut")), (9, 3))
        empty = Env(self.defs, None, 0)
        self.assertEqual([empty.lit(f"te_jmap_{v}") for v in ("states", "cut", "shown_states", "shown_cut")], [0] * 4)


class TwinTest(unittest.TestCase):
    """A map a system's own entry draws too has two ranges: the entry's, and the Map Room's twin under its options."""

    @classmethod
    def setUpClass(cls):
        cls.defs = trees(_read(OUT))

    def test_each_entry_map_has_a_twin_on_the_same_curve(self):
        self.assertEqual([s["name"] for s in gen.SCALES if s.get("twin_of")], ["gw_room", "gm_room"])
        for twin in (s for s in gen.SCALES if s.get("twin_of")):
            base = SCALES_BY_NAME[twin["twin_of"]][0]
            for key in ("input", "guards", "three", "sel", "where", "world", "min_span"):
                self.assertEqual(twin[key], base[key], (twin["name"], key))
            self.assertTrue(base.get("entry") and gen.in_room(twin) and not gen.in_room(base))

    def test_the_twin_is_the_entry_s_until_measured_and_its_own_after(self):
        for twin in (s for s in gen.SCALES if s.get("twin_of")):
            base = SCALES_BY_NAME[twin["twin_of"]][0]
            lo, hi = base["world"]["default"]
            span = hi - lo
            world = {f"te_jmap_rng_{base['name']}_lo": lo + span * 0.1, f"te_jmap_rng_{base['name']}_hi": lo + span * 0.7}
            europe = {f"te_jmap_rng_{twin['name']}_lo": lo + span * 0.3, f"te_jmap_rng_{twin['name']}_hi": lo + span * 0.4}
            for x in (lo, lo + span * 0.2, lo + span * 0.35, lo + span * 0.6, hi):
                def factor(scale, globs):
                    return Env(self.defs, scale["input"], x, globs=globs).run(self.defs[f"te_jmap_{scale['name']}_factor"])
                with self.subTest(twin=twin["name"], x=x):
                    # unmeasured: the entry's range, so a save from before the twin paints the Map Room as it did
                    self.assertAlmostEqual(factor(twin, world), factor(base, world))
                    # measured over an area: its own, and the entry's page is untouched by it
                    both = dict(world, **europe)
                    self.assertAlmostEqual(factor(base, both), factor(base, world))
                    self.assertAlmostEqual(factor(twin, both), gen.world_factor(
                        twin, europe[f"te_jmap_rng_{twin['name']}_lo"], europe[f"te_jmap_rng_{twin['name']}_hi"], x),
                        delta=1e-4)


class State:
    """A made-up state: its figure (or figures, by input token), whether the map paints it (its `where` holds),
    whether it is in the Map Room's area, and the variables script has put on it."""

    def __init__(self, x, painted=True, inside=True):
        self.x, self.painted, self.inside, self.vars = x, painted, inside, {}


INPUTS = frozenset(s["input"] for s in gen.SCALES)
WHERES = {tuple(s["where"]) for s in FITTED}


class Run:
    """The generated effects, run over made-up states the way the engine would run them: globals, state
    variables, every_state, ordered_state by position (a place past the end takes the last state, as the engine
    does: it doesn't skip) or from min to max, and scripted effects with their arguments. A list's limit is taken
    apart: the map's own `where` is the state's `painted`, te_jmap_in_area its `inside`, and a test of a figure or
    of a stored place is worked out."""

    def __init__(self, test, effects, values, states, named=None, globs=None):
        self.test, self.effects, self.values, self.states = test, effects, values, states
        self.named, self.globs = dict(named or {}), dict(globs or {})
        self.clamped, self.walked = [], 0

    def env(self, state=None):
        named, absent = dict(self.named), ()
        if state is not None:
            if "te_jmap_rank" in state.vars:
                named["var:te_jmap_rank"] = state.vars["te_jmap_rank"]
            else:
                absent = ("te_jmap_rank",)
        return Env(self.values, INPUTS, state.x if state is not None else 0, globs=self.globs, fixed=True,
                   named=named, absent=absent)

    def value(self, token, state=None):
        return self.env(state).lit(token)

    def listed(self, limit):
        where, tests = [], []
        for key, arg in limit:
            if key == "compare" and arg[0].endswith("_input"):
                tests.append((key, arg))
            elif key.endswith("_input") or (key, arg) in (("has_variable", "te_jmap_rank"), ("te_jmap_in_area", "yes")):
                tests.append((key, arg))
            else:
                where.append("%s %s %s" % arg if key == "compare" else f"{key} = {arg}")
        self.test.assertIn(tuple(where), WHERES, "a list that isn't a map's")
        out = []
        for state in self.states:
            if where and not state.painted:
                continue
            keep = True
            for key, arg in tests:
                if (key, arg) == ("te_jmap_in_area", "yes"):
                    keep = keep and state.inside
                elif (key, arg) == ("has_variable", "te_jmap_rank"):
                    keep = keep and "te_jmap_rank" in state.vars
                else:
                    keep = keep and self.env(state).holds([(key, arg)])
            if keep:
                out.append(state)
        return out

    def run(self, block, args=None, state=None):
        args = args or {}
        taken = False
        for key, arg in block:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    taken = False
                if taken:
                    continue
                if key != "else" and not self.env(state).holds(dict(arg).get("limit", [])):
                    continue
                taken = True
                self.run([p for p in arg if p[0] != "limit"], args, state)
            elif key == "debug_log":
                continue
            elif key == "remove_global_variable":
                del self.globs[arg]
            elif key == "set_global_variable":
                if isinstance(arg, str):
                    self.globs[arg] = 1.0
                else:
                    d = dict(arg)
                    self.globs[d["name"]] = self.value(d["value"], state)
            elif key == "change_global_variable":
                d = dict(arg)
                self.globs[d["name"]] += float(d["add"])
            elif key == "set_variable":
                self.test.assertIsNotNone(state, "set_variable outside a state")
                if isinstance(arg, str):
                    state.vars[arg] = 1.0
                else:
                    d = dict(arg)
                    state.vars[d["name"]] = self.value(d["value"], state)
            elif key == "remove_variable":
                del state.vars[arg]
            elif key == "every_state":
                body = [p for p in arg if p[0] != "limit"]
                for each in self.listed(dict(arg).get("limit", [])):
                    self.run(body, args, each)
            elif key == "ordered_state":
                d = dict(arg)
                self.test.assertEqual(d["check_range_bounds"], "no")
                rows = self.listed(d.get("limit", []))
                rows.sort(key=lambda each: self.value(d["order_by"], each), reverse=True)
                body = [p for p in arg if p[0] not in ("limit", "order_by", "position", "min", "max",
                                                        "check_range_bounds")]
                if "position" in d:
                    pos = int(d["position"].replace("$K$", str(args.get("K", ""))))
                    if not rows:
                        continue
                    if pos >= len(rows):
                        self.clamped.append(pos)
                        pos = len(rows) - 1
                    rows = [rows[pos]]
                else:
                    self.test.assertEqual(d["min"], "0")
                    self.test.assertLess(len(rows), int(d["max"]), "more states than the walk visits")
                    self.walked += 1
                for each in rows:
                    self.run(body, args, each)
            else:
                name = key.replace("$MAP$", args.get("MAP", ""))
                self.test.assertIn(name, self.effects, key)
                self.run(self.effects[name], dict(arg) if isinstance(arg, list) else args, state)


class RangeRunTest(unittest.TestCase):
    """The range effects, run over made-up states as the engine would run them (Run): the count, the trim, the
    ladder and the two ordered picks, against a plain sort. Each state is (figure, the map paints it, it is in the
    area)."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(EFFECTS_OUT)
        cls.effects = trees(cls.text)
        cls.values = trees(_read(OUT))

    def run_range(self, scale, states, option=0, area=0):
        n = gen.range_name(scale)
        run = Run(self, self.effects, self.values, [State(*each) for each in states],
                  named={"te_jmap_trim": option, "te_jmap_area": area},
                  globs={"te_jmap_rng_%s_lo" % n: -1, "te_jmap_rng_%s_hi" % n: -1})     # stale, from the last measure
        run.run(self.effects[f"te_jmap_range_{n}"])
        return run.globs, run.clamped

    def expect(self, states, limited, option=0, area=0):
        xs = sorted(x for x, painted, inside in states if painted and (inside or not limited))
        if not xs:
            return None
        k = gen.trim_count(len(xs), option, limited=area > 0)
        return xs[k], xs[-1 - k], len(xs), k

    def states(self, count, inside_every=1):
        # distinct figures, shuffled; every third state the map doesn't paint; one in inside_every in the area
        return [(float((i * 37) % 1009) + 1, i % 3 != 0, i % inside_every == 0) for i in range(count)]

    def test_a_range_is_the_sort_s(self):
        scale = SCALES_BY_NAME["gini"][0]
        n = "gini"
        for count in (0, 1, 2, 3, 4, 5, 8, 14, 15, 16, 30, 61, 200, 700, 2600):
            for option in (gen.TRIM_DEFAULT, gen.TRIM_NONE, gen.TRIM_PERCENT):
                for area, inside_every in ((0, 1), (1, 2), (4, 7)):
                    states = self.states(count, inside_every)
                    globs, clamped = self.run_range(scale, states, option, area)
                    want = self.expect(states, limited=True, option=option, area=area)
                    with self.subTest(count=count, option=option, area=area):
                        self.assertEqual(clamped, [], "a position past the end of the list")
                        if want is None:
                            # no state with a figure: the stale range is gone, and the curve's own ends serve
                            self.assertNotIn(f"te_jmap_rng_{n}_lo", globs)
                            self.assertNotIn(f"te_jmap_rng_{n}_hi", globs)
                            continue
                        lo, hi, states_in, k = want
                        self.assertEqual((globs[f"te_jmap_rng_{n}_lo"], globs[f"te_jmap_rng_{n}_hi"]), (lo, hi))
                        self.assertLessEqual(lo, hi)
                        self.assertEqual((globs["te_jmap_shown_n"], globs["te_jmap_shown_k"]), (states_in, k))

    def test_an_entry_s_range_ignores_the_options(self):
        # Emissions' own range (je_global_warming's): the whole world on the default trim while the Map Room is
        # limited to a seventh of it with no trim; the Map Room's twin follows the options
        entry, twin = SCALES_BY_NAME["gw"][0], SCALES_BY_NAME["gw_room"][0]
        states = self.states(300, inside_every=7)
        for option, area in ((gen.TRIM_NONE, 1), (gen.TRIM_PERCENT, 4), (gen.TRIM_DEFAULT, 0)):
            mine, _ = self.run_range(entry, states, option, area)
            theirs, _ = self.run_range(twin, states, option, area)
            with self.subTest(option=option, area=area):
                lo, hi, _n, _k = self.expect(states, limited=False)
                self.assertEqual((mine["te_jmap_rng_gw_lo"], mine["te_jmap_rng_gw_hi"]), (lo, hi))
                self.assertNotIn("te_jmap_shown_n", mine)
                lo, hi, _n, _k = self.expect(states, limited=True, option=option, area=area)
                self.assertEqual((theirs["te_jmap_rng_gw_room_lo"], theirs["te_jmap_rng_gw_room_hi"]), (lo, hi))

    def test_under_the_default_options_a_range_is_the_old_fifth_from_each_end(self):
        # what te_jmap_range_<map> gave before the options: position = 4 from the top and from the bottom
        scale = SCALES_BY_NAME["turmoil"][0]
        states = [(float((i * 53) % 997), True, True) for i in range(640)]
        globs, _ = self.run_range(scale, states)
        xs = sorted(x for x, _p, _i in states)
        self.assertEqual((globs["te_jmap_rng_turmoil_lo"], globs["te_jmap_rng_turmoil_hi"]), (xs[4], xs[-5]))


MIDS = [s for s in ROOM if s["world"]["kind"] == "mid"]
SETTINGS = {"linear": gen.SCALE_LINEAR, "logarithmic": gen.SCALE_LOG}


class ScaleTest(unittest.TestCase):
    """The Scale option: each factor the Map Room reads, under Linear and Logarithmic, against the generator's
    reference; Ranked reads the stored place."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(OUT)
        cls.defs = trees(cls.text)

    factor = ScalesTest.factor

    def test_each_tree_follows_its_scale(self):
        # the committed tree against gen.scaled_factor, in floats and in the engine's five decimals, for each
        # measured range the own curve is tested on
        for scale in ROOM:
            for name, option in SETTINGS.items():
                for rng in ranges(scale):
                    globs = store(scale, rng)
                    for x in samples(scale, rng):
                        want = gen.scaled_factor(scale, option, *(rng or (None, None)), x)
                        for fixed, delta in ((False, 1e-4), (True, 5e-3)):
                            with self.subTest(map=scale["name"], scale=name, range=rng, x=x, fixed=fixed):
                                self.assertAlmostEqual(self.factor(scale, x, globs=globs, fixed=fixed, option=option),
                                                       want, delta=delta)

    def test_each_scale_rises_and_spans_the_range(self):
        for scale in ROOM:
            w = scale["world"]
            for name, option in SETTINGS.items():
                for rng in ranges(scale):
                    L, H = gen.world_bounds(scale, *(rng or (None, None)))
                    ys = [gen.scaled_factor(scale, option, *(rng or (None, None)), x) for x in samples(scale, rng)]
                    low = gen.scaled_factor(scale, option, *(rng or (None, None)), L)
                    high = gen.scaled_factor(scale, option, *(rng or (None, None)), H)
                    with self.subTest(map=scale["name"], scale=name, range=rng):
                        self.assertEqual(ys, sorted(ys), "rising")
                        if w["kind"] == "mid" and H <= w["mid"]:
                            self.assertEqual((round(low, 9), round(high, 9)), (0.0, 0.5))
                        elif w["kind"] == "mid" and L >= w["mid"]:
                            self.assertEqual((round(low, 9), round(high, 9)), (0.5, 1.0))
                        elif option == gen.SCALE_LOG and w["kind"] == "frac":
                            # the low end is the range's low, or a 64th of its high where the low is smaller
                            self.assertEqual(round(high, 9), 1.0)
                            start = gen.log_start(scale, *(rng or (None, None)))
                            self.assertEqual(round(gen.scaled_factor(scale, option, *(rng or (None, None)), start), 9), 0.0)
                            self.assertEqual(start, max(L, H / gen.LOG_RATIO))
                        else:
                            self.assertEqual((round(low, 9), round(high, 9)), (0.0, 1.0))

    def test_linear_is_straight(self):
        # halfway along the range, half the color; on a midpoint map, halfway along each side
        for scale in ROOM:
            w = scale["world"]
            lo, hi = w["default"]
            got = lambda x: gen.scaled_factor(scale, gen.SCALE_LINEAR, lo, hi, x)   # noqa: E731
            with self.subTest(map=scale["name"]):
                if w["kind"] == "mid":
                    self.assertAlmostEqual(got((lo + w["mid"]) / 2), 0.25)
                    self.assertAlmostEqual(got((hi + w["mid"]) / 2), 0.75)
                else:
                    L, H = gen.world_bounds(scale, lo, hi)
                    self.assertAlmostEqual(got((L + H) / 2), 0.5)

    def test_logarithmic_gives_each_doubling_the_same_color(self):
        for scale in ROOM:
            w = scale["world"]
            if w["kind"] != "frac":
                continue
            lo, hi = w["default"]
            start = gen.log_start(scale, lo, hi)
            H = gen.world_bounds(scale, lo, hi)[1]
            steps = gen.log2_pieces(H / start)
            ys = [gen.scaled_factor(scale, gen.SCALE_LOG, lo, hi, start * 2 ** k) for k in range(int(steps) + 1)]
            with self.subTest(map=scale["name"]):
                for a, b in zip(ys, ys[1:]):
                    self.assertAlmostEqual(b - a, 1 / max(steps, 1))
                self.assertLessEqual(steps, math.log2(gen.LOG_RATIO) + 1e-9, "six doublings at most")

    def test_a_doubling_map_is_already_logarithmic(self):
        for scale in ROOM:
            if scale["world"]["kind"] != "doubling":
                continue
            for rng in ranges(scale):
                globs = store(scale, rng)
                for x in samples(scale, rng):
                    with self.subTest(map=scale["name"], range=rng, x=x):
                        self.assertEqual(self.factor(scale, x, globs=globs, fixed=True, option=gen.SCALE_LOG),
                                         self.factor(scale, x, globs=globs, fixed=True))

    def test_logarithmic_keeps_the_midpoint_and_is_straight_within_min_half(self):
        # the eight maps that run both ways from a midpoint (owner, 2026-11-14: "What about symlog?"): logarithmic
        # on each side by the distance from the midpoint, straight within min_half of it, and the midpoint at
        # exactly 0.5, which map_color's split and the neutral color rest on
        self.assertEqual(sorted(s["name"] for s in MIDS),
                         ["comfort", "comfort_base", "growth", "mig", "natural", "sex", "tfr", "wc"])
        for scale in MIDS:
            w = scale["world"]
            mid, h = w["mid"], w["min_half"]
            lo, hi = w["default"]
            self.assertEqual(gen.knee(scale), h / 2)
            for option in SETTINGS.values():
                for rng in ranges(scale):
                    L, H = gen.world_bounds(scale, *(rng or (None, None)))
                    if L < mid < H:
                        with self.subTest(map=scale["name"], scale=option, range=rng):
                            self.assertEqual(self.factor(scale, mid, globs=store(scale, rng), fixed=True,
                                                         option=option), 0.5)
            got = lambda x: gen.scaled_factor(scale, gen.SCALE_LOG, lo, hi, x)   # noqa: E731
            with self.subTest(map=scale["name"]):
                # straight to min_half on each side ...
                for sign in (1, -1):
                    self.assertAlmostEqual(got(mid + sign * h / 2) - 0.5, (got(mid + sign * h) - 0.5) / 2)
                    self.assertAlmostEqual(got(mid + sign * h / 4) - 0.5, (got(mid + sign * h) - 0.5) / 4)
                # ... then the same share of the color for each doubling of the distance, half the straight band's
                up = hi - mid
                if up >= 4 * h:
                    band = got(mid + h) - 0.5
                    self.assertAlmostEqual(got(mid + 2 * h) - got(mid + h), band / 2)
                    self.assertAlmostEqual(got(mid + 4 * h) - got(mid + 2 * h), band / 2)
                # and it is not the straight scale: more of the color near the midpoint
                self.assertGreater(got(mid + h) - 0.5, gen.scaled_factor(scale, gen.SCALE_LINEAR, lo, hi, mid + h) - 0.5)

    def test_the_logarithmic_start_survives_the_engine_s_five_decimals(self):
        # a low of 0 has no logarithm, so a straight map starts at a 64th of its high; on the narrowest range a
        # map can have (its low 0, its high min_span) the engine's five decimals must still hold that start
        for scale in ROOM:
            if scale["world"]["kind"] != "frac":
                continue
            n = scale["name"]
            with self.subTest(map=n):
                self.assertGreaterEqual(scale["min_span"] / gen.LOG_RATIO, gen.LOG_FLOOR)
                env = Env(self.defs, scale["input"], 0, fixed=True,
                          globs={f"te_jmap_rng_{n}_lo": 0, f"te_jmap_rng_{n}_hi": 0})
                self.assertGreaterEqual(env.lit(f"te_jmap_{n}_lg_min"), gen.LOG_FLOOR)
                # the figure over the start is worked out without dividing by the small start itself
                self.assertNotIn(f"divide = te_jmap_{n}_lg_min", self.text)
                # and a figure of 0 is the low color, not an error
                self.assertEqual(self.factor(scale, 0, fixed=True, option=gen.SCALE_LOG,
                                             globs={f"te_jmap_rng_{n}_lo": 0, f"te_jmap_rng_{n}_hi": 0}), 0.0)

    def test_ranked_reads_the_stored_place(self):
        for scale in ROOM:
            with self.subTest(map=scale["name"]):
                for rank in (0.0, 0.25, 0.5, 1.0):
                    self.assertEqual(self.factor(scale, 123.0, fixed=True, option=gen.SCALE_RANKED, rank=rank), rank)
                # no place yet (a state made since the measure): the midpoint color, or the low one
                self.assertEqual(self.factor(scale, 123.0, option=gen.SCALE_RANKED), 0.5 if scale["three"] else 0.0)
                body = effect_body(self.text, f"te_jmap_{scale['name']}_factor")
                self.assertIn("limit = { has_variable = te_jmap_rank }\n", body, "the place is read inside its guard")

    def test_the_default_is_the_map_s_own_curve_first(self):
        # one comparison on a default paint: the own curve is the switch's first branch
        for scale in ROOM:
            body = self.defs[f"te_jmap_{scale['name']}_factor"]
            if scale["guards"]:
                body = [p for p in dict(body)["if"] if p[0] != "limit"]
            keys = [k for k, _ in body if k not in ("min", "max")]
            with self.subTest(map=scale["name"]):
                self.assertEqual(keys, ["if", "else_if", "else_if", "else"])
                limits = [dict(arg).get("limit") for k, arg in body if k in ("if", "else_if")]
                self.assertEqual(limits, [[("te_jmap_scale", "0")], [("te_jmap_scale", "1")], [("te_jmap_scale", "2")]])

    def test_the_scale_is_the_map_room_s_alone(self):
        # a system's own entry reads its own factor (te_jmap_gw_factor, te_jmap_gm_factor), and the fixed curves
        # have no range to rescale: none of them reads the option or a stored place
        for scale in ENTRY + FIXED:
            tree = effect_body(self.text, f"te_jmap_{scale['name']}_factor")
            with self.subTest(map=scale["name"]):
                self.assertNotIn("te_jmap_scale", tree)
                self.assertNotIn("te_jmap_rank", tree)
        for scale in ENTRY:
            for extra in ("_lg_lo", "_sl_up_t", "_lg_t"):
                self.assertNotIn(f"te_jmap_{scale['name']}{extra} =", self.text)
        hand = _read(HAND)
        self.assertRegex(hand, r"te_jmap_scale = \{\s*value = 0\s*if = \{\s*limit = \{ has_global_variable = "
                         r"te_jmap_opt_scale \}\s*value = global_var:te_jmap_opt_scale\s*\}\s*\}")

    def test_the_knees_are_worth_a_logarithm(self):
        # how many doublings lie between the straight band's edge (min_half) and each map's default extreme: under
        # one, Logarithmic would be Linear in all but name. (Fertility's low side, 1 to 2.1, is the shortest.)
        doublings = {}
        for scale in MIDS:
            w = scale["world"]
            lo, hi = w["default"]
            doublings[scale["name"]] = (round(math.log2((w["mid"] - lo) / w["min_half"]), 1),
                                        round(math.log2((hi - w["mid"]) / w["min_half"]), 1))
        self.assertEqual(doublings, {"wc": (2.3, 2.3), "tfr": (1.1, 3.1), "natural": (3.0, 3.2), "sex": (2.0, 2.6),
                                     "mig": (3.6, 3.6), "comfort_base": (1.8, 4.7), "comfort": (1.8, 4.7),
                                     "growth": (4.0, 4.3)})
        self.assertGreaterEqual(min(min(pair) for pair in doublings.values()), 1)


class RankRunTest(unittest.TestCase):
    """Ranked: te_jmap_rank_<map> and the dispatch around it, run over made-up states (Run) against a plain sort
    with ties (gen.ranks). A paint can't sort, so a wrong place here is a wrong color with nothing in the log."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(EFFECTS_OUT)
        cls.effects = trees(cls.text)
        cls.values = trees(_read(OUT))

    def rank(self, scale, figures, painted=None, inside=None, stale=None, named=None):
        states = [State(x, painted[i] if painted else True, inside[i] if inside else True)
                  for i, x in enumerate(figures)]
        for i, value in (stale or {}).items():
            states[i].vars["te_jmap_rank"] = value
        run = Run(self, self.effects, self.values, states, named=named or {})
        run.run(self.effects[f"te_jmap_rank_{scale['name']}"])
        return states, run

    def check(self, scale, figures):
        states, run = self.rank(scale, figures)
        mid = scale["world"]["mid"] if scale["world"]["kind"] == "mid" else None
        want = gen.ranks(figures, mid)
        for i, state in enumerate(states):
            self.assertAlmostEqual(state.vars["te_jmap_rank"], want[i], delta=2e-5, msg=(scale["name"], i, figures[i]))
        self.assertEqual(run.globs.get("te_jmap_ranks"), 1.0, "the mark that places are stored")
        return [state.vars["te_jmap_rank"] for state in states]

    def test_places_are_the_sort_s(self):
        scale = SCALES_BY_NAME["gini"][0]
        for count in (1, 2, 3, 10, 61, 400, 2600):
            figures = [float((i * 37) % 4099) / 4099 for i in range(count)]
            got = self.check(scale, figures)
            with self.subTest(count=count):
                self.assertEqual(min(got), 0.0)
                if count > 1:
                    self.assertEqual(max(got), 1.0)
                    # evenly: each state a step of the same size, whatever the figures
                    steps = sorted(got)
                    for a, b in zip(steps, steps[1:]):
                        self.assertAlmostEqual(b - a, 1 / (count - 1), delta=3e-5)

    def test_equal_figures_share_a_place(self):
        # peacetime Devastation: hundreds of states at exactly 0 and a few torn ones. An index would smear the
        # zeros across most of the palette in whatever order the engine walks them; they share the lowest place,
        # and each distinct figure above them is one even step
        scale = SCALES_BY_NAME["devastation"][0]
        figures = [0.0] * 600 + [0.05, 0.2, 0.2, 0.4, 0.75] + [0.0] * 300
        got = self.check(scale, figures)
        self.assertEqual({got[i] for i, x in enumerate(figures) if x == 0.0}, {0.0})
        self.assertEqual([got[600], got[601], got[602], got[603], got[604]], [0.25, 0.5, 0.5, 0.75, 1.0])
        # every state alike: one place, the low color
        self.assertEqual(set(self.check(scale, [0.0] * 50)), {0.0})

    def test_a_midpoint_map_is_ranked_outward_on_each_side(self):
        # Fertility: cream stays at replacement (2.1), not at the median state. Each side's states step evenly from
        # the midpoint out to that side's full color, and a state exactly at the midpoint is the midpoint's color
        scale = SCALES_BY_NAME["tfr"][0]
        figures = [1.2, 1.9, 2.1, 2.2, 3.0, 4.5, 6.0, 1.9, 2.1]
        got = self.check(scale, figures)
        self.assertEqual(got, [0.0, 0.25, 0.5, 0.625, 0.75, 0.875, 1.0, 0.25, 0.5])
        # the whole world on one side: that side's colors alone, the nearest state just off the midpoint's
        above = self.check(scale, [2.5, 3.0, 4.0, 5.0])
        self.assertEqual(above, [0.625, 0.75, 0.875, 1.0])
        below = self.check(scale, [1.0, 1.5, 2.0])
        for value, want in zip(below, [0.0, 1 / 6, 1 / 3]):
            self.assertAlmostEqual(value, want, delta=2e-5)
        for scale in MIDS:
            mid = scale["world"]["mid"]
            lo, hi = scale["world"]["default"]
            figures = [lo + (hi - lo) * ((i * 7) % 23) / 22 for i in range(23)] + [mid, mid]
            with self.subTest(map=scale["name"]):
                got = self.check(scale, figures)
                for x, value in zip(figures, got):
                    self.assertEqual(value == 0.5, x == mid)
                    self.assertEqual(value < 0.5, x < mid)

    def test_only_the_states_the_map_measures_are_ranked(self):
        # the states the map paints with a figure, in the Map Room's area: a state outside either has no place
        scale = SCALES_BY_NAME["gini"][0]
        figures = [float(i) for i in range(40)]
        painted = [i % 3 != 0 for i in range(40)]
        inside = [i % 4 != 0 for i in range(40)]
        states, _run = self.rank(scale, figures, painted, inside)
        ranked = [i for i, state in enumerate(states) if "te_jmap_rank" in state.vars]
        self.assertEqual(ranked, [i for i in range(40) if painted[i] and inside[i]])
        want = gen.ranks([figures[i] for i in ranked])
        for j, i in enumerate(ranked):
            self.assertAlmostEqual(states[i].vars["te_jmap_rank"], want[j], delta=2e-5)
        for scale in ROOM:
            body = effect_body(self.text, f"te_jmap_rank_{scale['name']}")
            limit = " ".join(gen.measured(scale))
            with self.subTest(map=scale["name"]):
                self.assertNotIn("\n\tlimit = {  }", body)
                for line in re.findall(r"\n\tlimit = \{ (.*) \}", body):
                    self.assertTrue(line.startswith(limit), "a walk or a pass over states the map doesn't measure")
                self.assertIn("te_jmap_in_area = yes", body)
                # by its own figure: Current Comfort shares Base Comfort's range, not its order
                self.assertRegex(body, rf"order_by = te_jmap_{scale['name']}_input(_neg)?\n")
                self.assertNotRegex(body, rf"order_by = te_jmap_(?!{scale['name']}_input)")
                self.assertNotRegex(body, r"\bposition\s*=", "a place is a count the walk keeps, not a position")
                self.assertEqual(body.count("min = 0\n"), body.count(f"max = {gen.RANK_MAX}\n"))
                self.assertEqual(body.count("check_range_bounds = no"), body.count("ordered_state = {"))

    def refresh(self, sel, option, states, stale_flag=True):
        run = Run(self, self.effects, self.values, states,
                  named={"te_jmap_selector": sel, "te_jmap_scale": option, "te_jmap_trim": 0, "te_jmap_area": 0},
                  globs={"te_jmap_ranks": 1.0} if stale_flag else {})
        run.run(self.effects["te_jmap_refresh_range"])
        return run

    def test_a_measure_takes_the_pick_s_places_and_clears_every_other(self):
        # one variable serves every map, so te_jmap_refresh_range clears it first: at a pick, an option click and
        # each month. Ranked, the pick's places follow its range; under any other scale none is left behind
        figures = [float((i * 37) % 101) for i in range(60)]

        def states():
            out = [State(x, painted=i % 5 != 0) for i, x in enumerate(figures)]
            for state in out:
                state.vars["te_jmap_rank"] = 0.77      # another map's, from the last pick
            return out

        made = states()
        run = self.refresh(16, gen.SCALE_RANKED, made)      # Gini, ranked
        want = gen.ranks([x for i, x in enumerate(figures) if i % 5 != 0])
        got = [state.vars.get("te_jmap_rank") for state in made]
        self.assertEqual([value is None for value in got], [i % 5 == 0 for i in range(60)],
                         "a state the map doesn't paint keeps no place from the map before")
        for j, value in enumerate(v for v in got if v is not None):
            self.assertAlmostEqual(value, want[j], delta=2e-5)
        self.assertIn("te_jmap_rng_gini_hi", run.globs, "the range is still measured: the tooltip prints it")
        for option in (gen.SCALE_OWN, gen.SCALE_LINEAR, gen.SCALE_LOG):
            made = states()
            run = self.refresh(16, option, made)
            with self.subTest(scale=option):
                self.assertEqual([state.vars for state in made], [{}] * 60)
                self.assertNotIn("te_jmap_ranks", run.globs)
                self.assertEqual(run.walked, 0, "no walk of the states for a scale that reads no place")
        # a pick with no range (Leading Cause): cleared, and nothing stored
        made = states()
        self.refresh(11, gen.SCALE_RANKED, made)
        self.assertEqual([state.vars for state in made], [{}] * 60)
        # and with no place stored anywhere, nothing is walked to clear
        body = effect_body(self.text, "te_jmap_clear_ranks")
        self.assertRegex(body, r"if = \{\n\t\tlimit = \{ has_global_variable = te_jmap_ranks \}\n\t\tevery_state = \{\n"
                         r"\t\t\tlimit = \{ has_variable = te_jmap_rank \}\n\t\t\tremove_variable = te_jmap_rank\n")

    def test_every_fitted_pick_has_its_own_places(self):
        body = effect_body(self.text, "te_jmap_refresh_rank")
        picked = {int(sel): name for sel, name in
                  re.findall(r"limit = \{ te_jmap_selector = (\d+) \}\s*(te_jmap_rank_\w+) = yes", body)}
        self.assertEqual(picked, {s["sel"]: f"te_jmap_rank_{s['name']}" for s in ROOM})
        self.assertEqual((picked[27], picked[28]), ("te_jmap_rank_comfort_base", "te_jmap_rank_comfort"))
        dispatch = effect_body(self.text, "te_jmap_refresh_range")
        self.assertLess(dispatch.index("te_jmap_clear_ranks = yes"), dispatch.index("te_jmap_selector = 1 }"))
        self.assertRegex(dispatch, r"if = \{\n\t\tlimit = \{ te_jmap_scale = 3 \}\n\t\tte_jmap_refresh_rank = yes\n\t\}\n\}$")
        # a range's own effect stores no place: the once-a-game range check measures GDP per capita whatever the
        # pick, and must not leave GDP's places under another map
        for scale in OWN:
            self.assertNotIn("te_jmap_rank", effect_body(self.text, f"te_jmap_range_{scale['name']}"))


class UseTest(unittest.TestCase):
    def test_the_map_reads_only_generated_factors(self):
        generated = set(re.findall(r"^(te_jmap_\w+)\s*=\s*\{", _read(OUT), re.M))
        used = set(re.findall(r"\b(te_jmap_\w+_factor(?:_lower|_upper)?)\b", _read(ROOM_FILE)))
        self.assertEqual(used - generated, set(), "factors the map reads that the generator doesn't write")
        theirs = set()
        for path in ENTRIES:
            mine = set(re.findall(r"\b(te_jmap_\w+_factor(?:_lower|_upper)?)\b", _read(path)))
            self.assertEqual(mine - generated, set(), f"{os.path.basename(path)}: factors no generator writes")
            theirs |= mine
        top = {n for n in generated if n.endswith("_factor")}
        three = {f"te_jmap_{s['name']}_factor" for s in gen.SCALES if s["three"]}
        self.assertEqual(top - used - theirs, set(), "generated factors no map reads")
        self.assertEqual({n for n in used if n.endswith("_lower")}, {n + "_lower" for n in three})

    def test_each_page_reads_its_own_factor_for_an_entry_map(self):
        # Emissions and Grandeur: the Map Room reads the twin, whose range follows its options; the system's own
        # entry reads the row's, whose range is the whole world's. One factor on both pages would grey nothing on
        # the entry's page but squeeze its colors into the Map Room's area's range.
        room = re.sub(r"#[^\n]*", "", _read(ROOM_FILE))
        for name, entry in (("gw", "je_global_warming"), ("gm", "je_grand_monuments")):
            own = re.sub(r"#[^\n]*", "", _read(os.path.join(REPO, "common", "journal_entries", f"{entry}.txt")))
            with self.subTest(map=name):
                self.assertIn(f"factor = te_jmap_{name}_room_factor", room)
                self.assertNotRegex(room, rf"\bte_jmap_{name}_factor\b", "the Map Room on the entry's range")
                self.assertIn(f"factor = te_jmap_{name}_factor", own)
                self.assertNotIn("_room_", own)
                self.assertNotIn("te_jmap_out", own)
                self.assertNotIn("te_jmap_in_area", own)

    def test_no_generated_value_by_hand(self):
        # two top-level script values with one name across files: the engine keeps one and drops the other silently
        generated = set(re.findall(r"^(te_jmap_\w+)\s*=\s*\{", _read(OUT), re.M))
        hand = set(re.findall(r"^(te_jmap_\w+)\s*=", _read(HAND), re.M))
        self.assertEqual(generated & hand, set())

    def test_a_three_color_split_reads_the_factor(self):
        # a raw threshold beside the factor would put the midpoint in two places
        room = _read(ROOM_FILE)
        for scale in gen.SCALES:
            if scale["three"]:
                with self.subTest(map=scale["name"]):
                    self.assertIn(f"te_jmap_{scale['name']}_factor < 0.5", room)


if __name__ == "__main__":
    unittest.main()
