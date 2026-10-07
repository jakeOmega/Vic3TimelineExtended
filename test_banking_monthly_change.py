"""The overview's monthly-change ranges hold what the monthly pulse can do.

Under each of the banking overview's first-row cells a line gives how far the
cycle value, momentum and bubble pressure can move at the next monthly update,
as a range worked out only from what the panels show (the modifier totals, the
momentum band, the policy stance band and the forecasting error's bound):
banking_disp_*_change_* in common/script_values/banking_overview_display_values.txt.

These tests run the pulse's own script, banking_cycle_bank_holiday_reopen and
banking_cycle_advance_variables, through a small interpreter over sampled
hidden states (the momentum figure inside its band, the stance gap and the
bank's forecasting error inside theirs, every branch of the random nudge), and
check that every outcome lands inside the range shown, and that each finite end
of a range is reached at some corner, so the range is no wider than it must be.
The stance band is worked out from the hidden gap with te_monetary_update_stance's
own thresholds, read from the effect, so a retuned threshold, decay or push
rate fails here until the display values follow it.
"""
import os
import random
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
DISP = os.path.join(REPO, "common", "script_values", "banking_overview_display_values.txt")
VALUE_FILES = [
    os.path.join(REPO, "common", "script_values", "extra_script_values.txt"),
    os.path.join(REPO, "common", "script_values", "te_monetary_script_values.txt"),
    DISP,
]
CYCLE_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "banking_cycle_effects.txt")
MON_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_monetary_effects.txt")
CUSTOM_LOC = os.path.join(REPO, "common", "customizable_localization", "banking_dash_custom_loc.txt")
DASH = os.path.join(REPO, "gui", "journal_entry_widgets", "banking_dashboard_widget.gui")
LOC = os.path.join(REPO, "localization", "english", "te_miscellaneous_l_english.yml")

READINGS = ("value", "momentum", "bubble")
EPS = 1e-6


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _parse(source):
    tokens = iter(ParadoxFileParser().tokenize(source))

    def body():
        out = []
        for key in tokens:
            if key == "}":
                return out
            op = next(tokens)
            value = next(tokens)
            out.append((key, op, body() if value == "{" else value.strip('"')))
        return out
    return body()


def _definitions(path):
    return {k: v for k, _, v in _parse(_read(path))}


def _block_from(text, start):
    j = text.index("{", start)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[j:k + 1]
    raise AssertionError("unbalanced block")


def stance_thresholds():
    """te_monetary_update_stance's band ladder: [(op, edge, band)], then the
    fallback band, read from the effect."""
    text = _read(MON_EFFECTS)
    at = text.index("set_variable = { name = te_mon_work value = var:te_mon_stance_gap }")
    ladder = text[at:text.index("else = {", at)]
    steps = re.findall(r"limit = \{ var:te_mon_work (<=|<) (-?[\d.]+) \}\s*"
                       r"set_variable = \{ name = te_mon_stance_band value = (\d) \}", ladder)
    rest = text[text.index("else = {", at):]
    last = int(re.search(r"name = te_mon_stance_band value = (\d)", rest).group(1))
    return [(op, float(edge), int(band)) for op, edge, band in steps], last


def gap_ceiling():
    """The +/-10 bound te_monetary_update_stance puts on the gap."""
    text = _read(MON_EFFECTS)
    return float(re.search(r"limit = \{ var:te_mon_stance_gap > ([\d.]+) \}", text).group(1))


def band_of(work, ladder):
    steps, last = ladder
    for op, edge, band in steps:
        if (work <= edge) if op == "<=" else (work < edge):
            return band
    return last


class World:
    """A country's variables, modifiers and the two triggers the pulse and
    the display values ask, plus just enough script to run them."""

    VALUES = None
    EFFECTS = None

    def __init__(self, variables, modifiers, *, holiday=False, has_stance=False):
        if World.VALUES is None:
            World.VALUES = {}
            for path in VALUE_FILES:
                World.VALUES.update(_definitions(path))
            World.EFFECTS = _definitions(CYCLE_EFFECTS)
        self.vars = dict(variables)
        self.mods = dict(modifiers)
        self.flags = {"banking_tool_bank_holiday_active": holiday, "te_mon_has_stance": has_stance}

    # --- script values ---------------------------------------------------
    def number(self, token):
        if isinstance(token, list):
            return self.value(token)
        if token.startswith("var:"):
            return self.vars[token[4:]]   # an unguarded read of a missing variable fails
        if token.startswith("modifier:"):
            return self.mods.get(token[len("modifier:"):], 0.0)
        if token in self.VALUES:
            return self.value(self.VALUES[token])
        return float(token)

    def value(self, body, initial=0.0):
        n = initial
        matched = False
        for key, _, val in body:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    matched = False
                if matched:
                    continue
                if key == "else" or self.check(self.field(val, "limit")):
                    n = self.value([x for x in val if x[0] != "limit"], n)
                    matched = True
                continue
            x = self.number(val)
            n = {"value": lambda: x, "add": lambda: n + x, "subtract": lambda: n - x,
                 "multiply": lambda: n * x, "divide": lambda: n / x,
                 "min": lambda: max(n, x), "max": lambda: min(n, x)}[key]()
        return n

    @staticmethod
    def field(body, name):
        return next(v for k, _, v in body if k == name)

    # --- triggers --------------------------------------------------------
    def check(self, body, mode="AND"):
        answers = []
        for key, op, val in body:
            if key in ("AND", "OR", "NOT"):
                answer = self.check(val, key)
            elif key == "has_variable":
                answer = val in self.vars
            elif key in self.flags:
                answer = self.flags[key] == (val == "yes")
            else:
                a, b = self.number(key), self.number(val)
                answer = {"=": a == b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
            answers.append(answer)
            if mode == "AND" and not answer:
                return False
        if mode == "NOT":
            return not any(answers)
        return any(answers) if mode == "OR" else all(answers)

    # --- effects, every random_list branch -------------------------------
    def copy(self):
        w = World(self.vars, self.mods)
        w.flags = dict(self.flags)
        return w

    def step(self, key, val):
        """One effect with no branches."""
        if key == "change_variable":
            name = self.field(val, "name")
            self.vars[name] = self.value([x for x in val if x[0] != "name"], self.vars[name])
        elif key == "set_variable":
            self.vars[self.field(val, "name")] = self.number(self.field(val, "value"))
        elif key == "remove_variable":
            self.vars.pop(val, None)
        else:
            raise AssertionError(f"unsupported effect {key}")

    def execute_chain(self, body):
        """Every state the effect body can leave: one per random_list branch
        whose weight is above 0 (`value =` in an entry's modifier replaces its
        literal weight, as banking_cycle_sim.py notes)."""
        worlds = [(self, False)]
        for item in body:
            key, _, val = item
            nxt = []
            for w, matched in worlds:
                if key in ("if", "else_if", "else"):
                    if key == "if":
                        matched = False
                    if not matched and (key == "else" or w.check(w.field(val, "limit"))):
                        for after in w.execute_chain([x for x in val if x[0] != "limit"]):
                            nxt.append((after, True))
                    else:
                        nxt.append((w, matched))
                elif key == "random_list":
                    for weight, _, branch in val:
                        mods = [v for k, _, v in branch if k == "modifier"]
                        wt = w.value(mods[0], float(weight)) if mods else float(weight)
                        if wt > 0:
                            for after in w.copy().execute_chain([x for x in branch if x[0] != "modifier"]):
                                nxt.append((after, False))
                else:
                    w.step(key, val)
                    nxt.append((w, False))
            worlds = nxt
        return [w for w, _ in worlds]

    def pulse(self):
        """The two steps of the monthly pulse that move the cycle's readings,
        in the pulse's order (je_banking.txt)."""
        out = []
        for w in self.copy().execute_chain(self.EFFECTS["banking_cycle_bank_holiday_reopen"]):
            out.extend(w.execute_chain(self.EFFECTS["banking_cycle_advance_variables"]))
        return out

    def shown(self, reading):
        lo = self.number(f"banking_disp_{reading}_change_lo")
        hi = self.number(f"banking_disp_{reading}_change_hi")
        shape = int(self.number(f"banking_disp_{reading}_change_shape"))
        return lo, hi, shape


# The momentum bands (banking_disp_momentum_band_code), the open ends of
# Freefall and Overheating cut where sampling stops.
MOMENTUM_BANDS = {1: (-8.0, -5.0), 2: (-5.0, -3.0), 3: (-3.0, -1.0), 4: (-1.0, 1.0),
                  5: (1.0, 3.0), 6: (3.0, 5.0), 7: (5.0, 8.0)}
LOW_EDGE_IN = {5, 6, 7}     # Rising, Surging and Overheating include their lower edge
HIGH_EDGE_IN = {1, 2, 3}    # Freefall, Collapsing and Falling their upper one


def momentum_in(band, rng):
    lo, hi = MOMENTUM_BANDS[band]
    m = rng.uniform(lo, hi)
    return min(max(m, lo if band in LOW_EDGE_IN else lo + 1e-9), hi if band in HIGH_EDGE_IN else hi - 1e-9)


def scenario(rng, ladder):
    """A hidden state, the inputs that make it, and its world."""
    band = rng.randint(1, 7)
    m = momentum_in(band, rng)
    mods = {
        "country_finance_value_monthly_add": rng.uniform(-1.5, 1.5),
        "country_finance_momentum_monthly_add": rng.uniform(-0.5, 0.5),
        "country_bubble_pressure_monthly_add": rng.uniform(-8, 8),
        "country_banking_random_momentum_mult": rng.uniform(-0.7, 0.8),
        "country_bank_forecast_error_add": rng.choice([0.0, -0.01]),
    }
    v = rng.uniform(20, 80)
    if rng.random() < 0.1:   # the nudge's weights read exactly 50
        v = 50 - mods["country_finance_value_monthly_add"]
    variables = {"finance_cycle_value": v, "finance_cycle_momentum": m,
                 "bubble_pressure": rng.uniform(20, 80)}
    holiday = rng.random() < 0.25
    if not holiday and rng.random() < 0.2:
        variables["banking_bank_holiday_reopening"] = 1
    has_stance = rng.random() < 0.7
    world = World(variables, mods, holiday=holiday, has_stance=has_stance)
    if has_stance:
        bound = world.number("te_mon_forecast_error_bound")
        gap = rng.uniform(-gap_ceiling(), gap_ceiling())
        err = rng.uniform(-bound, bound)
        world.vars["te_mon_stance_gap"] = gap
        world.vars["te_mon_stance_band"] = band_of(gap - err, ladder)
    elif rng.random() < 0.5:
        # what te_monetary_update_stance writes for a country with no stance
        world.vars["te_mon_stance_gap"] = 0
        world.vars["te_mon_stance_band"] = 3
    return world


def changes(before, after):
    return {
        "value": after.vars["finance_cycle_value"] - before.vars["finance_cycle_value"],
        "momentum": after.vars["finance_cycle_momentum"] - before.vars["finance_cycle_momentum"],
        "bubble": after.vars["bubble_pressure"] - before.vars["bubble_pressure"],
    }


def holds(shape, lo, hi, x):
    """Is x inside the range a line of this shape shows?"""
    above = x >= lo - EPS
    below = x <= hi + EPS
    return {1: above and below, 2: above, 3: below, 4: abs(x - lo) <= EPS}[shape]


class ContainmentTest(unittest.TestCase):
    """Every month the pulse can produce lands inside the range shown."""

    def test_every_outcome_is_inside_the_range(self):
        rng = random.Random(20261007)
        ladder = stance_thresholds()
        for i in range(3000):
            world = scenario(rng, ladder)
            shown = {r: world.shown(r) for r in READINGS}
            for after in world.pulse():
                for reading, delta in changes(world, after).items():
                    lo, hi, shape = shown[reading]
                    self.assertTrue(
                        holds(shape, lo, hi, delta),
                        f"case {i}: {reading} moved {delta:+.4f}, shown {lo:+.4f}..{hi:+.4f} "
                        f"(shape {shape}); vars {world.vars} mods {world.mods} flags {world.flags}")


class TightnessTest(unittest.TestCase):
    """Each finite end is reached: put the hidden figures at their edges
    (the momentum band's, the gap's for the stance band shown) and some
    branch of the nudge lands on it."""

    def corners(self, world, ladder):
        band = int(world.number("banking_disp_momentum_band_code"))
        lo, hi = MOMENTUM_BANDS[band]
        ms = [x for x, open_end in ((lo, band == 1), (hi, band == 7)) if not open_end]
        gaps = [world.vars.get("te_mon_stance_gap", 0)]
        if world.flags["te_mon_has_stance"] and "te_mon_stance_band" in world.vars:
            bound = world.number("te_mon_forecast_error_bound")
            ceiling = gap_ceiling()
            steps = int(2 * ceiling / 0.01)
            fits = [-ceiling + k * 0.01 for k in range(steps + 1)
                    if any(band_of(-ceiling + k * 0.01 - e, ladder) == world.vars["te_mon_stance_band"]
                           for e in (-bound, bound))]
            gaps = [min(fits), max(fits)]
        for m in ms:
            for gap in gaps:
                w = world.copy()
                w.vars["finance_cycle_momentum"] = m
                if "te_mon_stance_gap" in w.vars:
                    w.vars["te_mon_stance_gap"] = gap
                yield w

    def test_finite_ends_are_reached(self):
        rng = random.Random(7)
        ladder = stance_thresholds()
        for i in range(400):
            world = scenario(rng, ladder)
            shown = {r: world.shown(r) for r in READINGS}
            seen = {r: [] for r in READINGS}
            for corner in self.corners(world, ladder):
                for after in corner.pulse():
                    for reading, delta in changes(corner, after).items():
                        seen[reading].append(delta)
            for reading in READINGS:
                lo, hi, shape = shown[reading]
                with self.subTest(case=i, reading=reading):
                    if shape in (1, 2, 4):
                        self.assertAlmostEqual(min(seen[reading]), lo, delta=0.02)
                    if shape in (1, 3, 4):
                        self.assertAlmostEqual(max(seen[reading]), hi, delta=0.02)


class OpenBandTest(unittest.TestCase):
    """Momentum's outer bands leave a range open on one side, and only there."""

    def shapes(self, momentum, holiday=False):
        w = World({"finance_cycle_value": 70, "finance_cycle_momentum": momentum, "bubble_pressure": 40},
                  {}, holiday=holiday)
        return {r: w.shown(r)[2] for r in READINGS}

    def test_shapes(self):
        self.assertEqual(self.shapes(5), {"value": 2, "momentum": 3, "bubble": 4})       # Overheating
        self.assertEqual(self.shapes(-5), {"value": 3, "momentum": 2, "bubble": 4})      # Freefall
        self.assertEqual(self.shapes(4.9), {"value": 1, "momentum": 1, "bubble": 4})     # Surging
        self.assertEqual(self.shapes(-4.9), {"value": 1, "momentum": 1, "bubble": 4})    # Collapsing
        # momentum floored at 0 for the month: the cycle value cannot move
        self.assertEqual(self.shapes(-5, holiday=True), {"value": 4, "momentum": 2, "bubble": 4})
        self.assertEqual(self.shapes(0), {"value": 1, "momentum": 1, "bubble": 4})

    def test_the_example_from_the_request(self):
        """Steady momentum spans -1 to +1, so with nothing else moving the
        cycle and the cycle at 50 (no nudge), the value range is the band's
        span after the decay, about -0.9 to +0.9."""
        w = World({"finance_cycle_value": 50, "finance_cycle_momentum": 0.2, "bubble_pressure": 10}, {})
        lo, hi, shape = w.shown("value")
        self.assertEqual(shape, 1)
        self.assertAlmostEqual(lo, -0.9)
        self.assertAlmostEqual(hi, 0.9)


class DisplayTest(unittest.TestCase):
    """The lines and their words."""

    def test_band_edges_follow_the_band_words(self):
        text = _read(CUSTOM_LOC)

        def tests(name):
            block = _block_from(text, re.search(rf"(?m)^{name} = \{{", text).end() - 1)
            return [" ".join(t.split()) for t in re.findall(r"trigger = \{(.*?)\}\s*localization_key", block, re.S)]
        self.assertEqual(tests("banking_dash_momentum_band_edges"), tests("banking_dash_momentum_band"))

    def test_every_shape_has_a_line(self):
        dash = _read(DASH)
        loc = _read(LOC)
        produced = {"value": {1, 2, 3, 4}, "momentum": {1, 2, 3, 4}, "bubble": {1, 4}}
        for reading, shapes in produced.items():
            with self.subTest(reading=reading):
                found = re.findall(
                    rf"ScriptValue\('banking_disp_{reading}_change_shape'\), '\(CFixedPoint\)(\d)' \)\]\"\s*"
                    rf"text = \"(banking_dash_{reading}_change_\w+)\"", dash)
                self.assertEqual({int(s) for s, _ in found}, shapes)
                for _, key in found:
                    self.assertRegex(loc, rf"(?m)^ {key}:0 \"")
                self.assertIn(f'tooltip = "banking_dash_{reading}_change_tt"', dash)
                self.assertRegex(loc, rf"(?m)^ banking_dash_{reading}_change_tt:0 \"")

    def test_the_status_text_is_gone(self):
        """Its three modifier totals live in the lines' tooltips now."""
        loc = _read(LOC)
        for reading, modifier in (("value", "country_finance_value_monthly_add"),
                                  ("momentum", "country_finance_momentum_monthly_add"),
                                  ("bubble", "country_bubble_pressure_monthly_add")):
            line = re.search(rf"(?m)^ banking_dash_{reading}_change_tt:0 \"(.*)\"$", loc).group(1)
            self.assertIn(f"GetValueWithBreakdownFor('{modifier}')", line)


if __name__ == "__main__":
    unittest.main()
