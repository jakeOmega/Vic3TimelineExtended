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
            elif key == "modulo":
                # C++'s % keeps the dividend's sign; the generated phases keep it positive.
                assert acc >= 0, "a negative dividend"
                acc = acc % self.number(value, month)
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
        for rel in (glw.TRIGGERS_OUT, glw.VALUES_OUT, glw.LEGS_OUT):
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


# ---------------------------------------------------------------------------
# The gate's script
# ---------------------------------------------------------------------------
def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*\{", text)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth, i = 0, m.end() - 1
    for j in range(i, len(text)):
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        if depth == 0:
            return text[m.end():j]
    raise AssertionError("unclosed block")


class GateScriptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw("common", "scripted_effects", "space_race_effects.txt"))
        cls.windows = _strip(_raw("common", "scripted_effects", "sr_launch_window_effects.txt"))
        # The draw is generated from the site table (gen_solar_sites.py).
        cls.colony = _block(_strip(_raw("common", "scripted_effects", "sr_sites_generated.txt")),
                            "sr_establish_colony_effect")
        cls.site_body = {site: b.key for b in glw.BODIES for site in b.sites}

    def test_every_colony_site_is_drawn_through_its_window_body(self):
        branches = re.findall(r"trigger = \{(.*?)\}\s*set_global_variable = \{ name = sr_colony_(\w+) value = yes \}(.*?)"
                              r"trigger_event", self.colony, re.S)
        sites = {site for _, site, _ in branches}
        self.assertEqual(sites, set(self.site_body) | set(glw.UNGATED_SITES))
        # Each stage also draws the released worlds of the stages before it
        # (colony record design § 6): a world is listed once per stage from its own.
        stage_of = {site: b.stage for b in glw.BODIES for site in b.sites} | dict(glw.UNGATED_SITES)
        self.assertEqual(len(branches), sum(6 - stage_of[site] for site in sites))
        for trigger, site, effect in branches:
            with self.subTest(site=site):
                self.assertIn(f"NOT = {{ has_global_variable = sr_colony_{site} }}", trigger)
                if site in glw.UNGATED_SITES:
                    self.assertIn("sr_launch_ungated_departs = yes", trigger)
                    self.assertNotIn("sr_launch_window_gate_check", effect)
                else:
                    body = self.site_body[site]
                    self.assertEqual(re.findall(r"sr_launch_site_departs = \{ BODY = (\w+) \}", trigger), [body])
                    self.assertEqual(re.findall(r"sr_launch_window_gate_check = \{ BODY = (\w+) \}", effect), [body])

    def test_each_stage_holds_its_bodies_sites(self):
        draws = self.colony[:self.colony.index("local_var:sr_colonies_claimed_before < sr_total_global_colonies")]
        stages = re.split(r"global_var:sr_colonization_stage = (\d)", draws)
        for i in range(1, len(stages), 2):
            stage, body = int(stages[i]), stages[i + 1]
            drawn = set(re.findall(r"name = sr_colony_(\w+) value = yes", body))
            # Its own worlds, and the released worlds of the stages before it.
            expected = {s for b in glw.BODIES if b.stage <= stage for s in b.sites}
            expected |= {s for s, st in glw.UNGATED_SITES.items() if st <= stage}
            with self.subTest(stage=stage):
                self.assertEqual(drawn, expected)

    def test_the_cache_and_the_panel_list_every_body(self):
        keys = [b.key for b in glw.BODIES]
        cache = _block(self.windows, "sr_launch_windows_refresh_cache")
        self.assertEqual(re.findall(r"sr_launch_window_cache_body = \{ BODY = (\w+) \}", cache), keys)
        lines = _block(self.windows, "sr_launch_window_lines")
        self.assertEqual(re.findall(r"sr_launch_window_line = \{ BODY = (\w+) \}", lines), keys)

    def test_the_journal_entry_launches_through_the_rule(self):
        je = _strip(_raw("common", "journal_entries", "je_space_race.txt"))
        entry = _block(je, "je_space_race_solar_colonization")
        pulse = entry[entry.index("on_monthly_pulse"):]
        self.assertIn("sr_launch_month = yes", pulse)
        self.assertNotIn("sr_establish_colony_effect", pulse)
        month = _block(self.windows, "sr_launch_month")
        self.assertLess(month.index("sr_launch_windows_ensure_cache = yes"), month.index("sr_launch_fleet_ready"))
        # Spent only on a claim, at the cost read before the stage can move.
        self.assertLess(month.index("value = sr_launch_fleet_cost"), month.index("sr_establish_colony_effect = yes"))
        self.assertIn("local_var:sr_launch_claimed_before < sr_total_global_colonies", month)

    def test_setbacks_reach_solar_colonization_through_the_capped_loss(self):
        body = _block(self.effects, "sr_setback_lose_months")
        self.assertIn("sr_setback_lose_months_base = { MILESTONE = solar_colonization MONTHS = $MONTHS$ }", body)
        base = _block(self.effects, "sr_setback_lose_months_base")
        self.assertIn("sr_lose_progress_months = { MILESTONE = $MILESTONE$ MONTHS = $MONTHS$ }", base)
        self.assertNotIn("sr_apply_solar_colonization_progress_loss", self.windows)

    def test_a_loss_takes_one_goal_at_most(self):
        # loss = min(months x pace, goal, progress): staged fleets past one goal
        # are never touched, and progress never goes below zero.
        body = _block(self.effects, "sr_lose_progress_months")
        steps = re.findall(r"(value|multiply|max) = (\S+)", body)
        self.assertEqual(steps, [("value", "sr_event_pace_value"), ("multiply", "$MONTHS$"),
                                 ("max", "sr_$MILESTONE$_goal"), ("max", "var:sr_progress_$MILESTONE$")])
        goal = 400.0
        for progress in (10.0, 400.0, 1000.0):
            for loss_wanted in (30.0, 500.0):
                loss = min(loss_wanted, goal, progress)
                after = progress - loss
                self.assertGreaterEqual(after, 0)
                self.assertGreaterEqual(after, progress - goal)

    def test_global_variable_reads_are_guarded(self):
        values = _strip(_raw("common", "script_values", "sr_launch_window_values.txt"))
        values += _strip(_raw("common", "script_values", "sr_launch_windows_generated.txt"))
        for var in set(re.findall(r"global_var:(\w+)", values)):
            with self.subTest(var=var):
                for m in re.finditer(rf"global_var:{var}\b", values):
                    guard = values[max(0, m.start() - 160):m.start()]
                    self.assertIn(f"has_global_variable = {var}", guard)

    def test_every_body_has_its_panel_lines(self):
        # organize_loc files the keys by shape, so read every English loc file.
        loc_dir = os.path.join(REPO, "localization", "english")
        keys = set()
        for name in sorted(os.listdir(loc_dir)):
            if name.endswith(".yml"):
                with open(os.path.join(loc_dir, name), encoding="utf-8-sig") as f:
                    keys |= set(re.findall(r"(?m)^ (\w+):0 ", f.read()))
        for b in glw.BODIES:
            for kind in ("name", "line_open", "line_wait", "line_paid", "line_verdict"):
                with self.subTest(body=b.key, kind=kind):
                    self.assertIn(f"sr_window_{kind}_{b.key}", keys)


class NumberRangeTest(unittest.TestCase):
    """The script's numbers are fixed-point, about +-2.1 million."""

    def test_never_is_above_every_premium_and_its_arithmetic_stays_in_range(self):
        values = _strip(_raw("common", "script_values", "sr_launch_window_values.txt"))
        never = float(re.search(r"sr_launch_never = \{\s*value = ([\d.]+)", values).group(1))
        self.assertGreater(never, glw.PREMIUM_CAP)
        highest_goal = 650
        self.assertLess((1 + never) * highest_goal, 2_000_000)  # sr_launch_fleet_cost
        self.assertLess(highest_goal * glw.PREMIUM_CAP / 0.5, 2_000_000)  # sr_launch_months_cost_<body>, pace floor
        self.assertLess(never * 2, 2_000_000)  # sr_launch_months_allowed


class MoonTest(unittest.TestCase):
    """The Moon (lunar colonization design § 3.3): no window, no transit, and
    Shackleton's Propellant Depot standing in for Asteroid Mining's depots."""

    def test_the_ungated_worlds_are_the_table_s_bodyless_worlds(self):
        sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
        import gen_solar_sites as gss
        self.assertEqual(glw.UNGATED_SITES, {s.key: s.stage for s in gss.SITES if s.body is None})
        self.assertEqual([b.key for b in glw.TRANSIT_ONLY], ["mercury", "moon"])
        moon = next(t for t in glw.plan_transit_all() if t.body.key == "moon")
        self.assertEqual(set(moon.transit.values()), {0})
        values = _strip(_raw("common", "script_values", "sr_launch_windows_generated.txt"))
        for drive in glw.DRIVES:
            self.assertIn(f"sr_transit_{drive.key}_moon = {{ value = 0 }}", values)
        for name in ("sr_launch_best_cost", "sr_window_stage_wait"):
            with self.subTest(value=name):
                self.assertIn("if = { limit = { sr_window_moon_in_play = yes } max = 0 }", _block(values, name))
        triggers = _strip(_raw("common", "scripted_triggers", "sr_launch_windows_generated.txt"))
        in_play = _block(triggers, "sr_window_moon_in_play")
        self.assertEqual(re.findall(r"NOT = \{ has_global_variable = sr_colony_(\w+) \}", in_play),
                         [s.key for s in gss.LUNAR])
        # Mercury's old trigger is gone everywhere: the Moon departs by the same one.
        for top in ("common", "events"):
            for root, _, files in os.walk(os.path.join(REPO, top)):
                for name in files:
                    if name.endswith(".txt"):
                        with self.subTest(file=name):
                            self.assertNotIn("sr_launch_mercury_departs", _raw(root, name))
        hand = _strip(_raw("common", "scripted_triggers", "sr_launch_window_triggers.txt"))
        self.assertEqual(_block(hand, "sr_launch_ungated_departs").split(), ["sr_launch_best_cost", "<=", "0"])

    def test_shackleton_s_depot_is_a_propellant_depot(self):
        hand = _strip(_raw("common", "scripted_triggers", "sr_launch_window_triggers.txt"))
        depots = _block(hand, "sr_launch_has_depots")
        self.assertIn("has_technology_researched = asteroid_mining", depots)
        self.assertIn("modifier:country_sr_propellant_depots_bool = yes", depots)
        record = _block(hand, "sr_depots_by_record")
        for line in ("global_var:sr_site_holder_shackleton ?= this", "sr_site_lvl_a_value_shackleton >= 1",
                     "NOT = { has_global_variable = sr_site_blockaded_shackleton }",
                     "NOT = { has_global_variable = sr_site_occupier_shackleton }"):
            self.assertIn(line, record)
        types = _strip(_raw("common", "modifier_type_definitions", "space_race_modifier_types.txt"))
        self.assertIn("boolean = yes", _block(types, "country_sr_propellant_depots_bool"))
        modifiers = _strip(_raw("common", "static_modifiers", "space_race_modifiers.txt"))
        self.assertIn("country_sr_propellant_depots_bool = yes", _block(modifiers, "sr_colony_shackleton_depot"))
        # The self-check compares the boolean with the record each month (two strikes for BROKEN).
        effects = _strip(_raw("common", "scripted_effects", "sr_launch_window_effects.txt"))
        self.assertIn("sr_depots_self_check = yes", _block(effects, "sr_launch_month"))
        check = _block(effects, "sr_depots_self_check")
        self.assertIn("sr_depots_by_record = yes", check)
        self.assertIn("sr_depots_mismatch_months", check)


class DebugLineTest(unittest.TestCase):
    """A $PARAM$ inside a debug_log string is mangled (scripting_best_practices.md, "No $PARAM$ inside the
    string"): the self-checks and the console copy figures into fixed-name globals and name the body by code."""

    FILES = (("common", "scripted_effects", "sr_launch_window_effects.txt"),
             ("common", "scripted_effects", "te_debug_launch_window_effects.txt"))

    def test_no_parameter_inside_a_debug_line(self):
        for parts in self.FILES:
            for line in re.findall(r'debug_log = "([^"]*)"', _raw(*parts)):
                with self.subTest(file=parts[-1], line=line[:60]):
                    self.assertNotIn("$", line)

    def test_self_check_lines_spell_out_the_generator_s_body_codes(self):
        effects = _raw(*self.FILES[0])
        gate = _block(_strip(effects), "sr_launch_window_gate_check")
        self.assertEqual(gate.count("sr_window_log_copy = { BODY = $BODY$ }"), 3)
        lines = re.findall(r'debug_log = "(TE_SELF_CHECK \w+ window_gate[^"]*)"', effects)
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertIn(f"({glw.BODY_CODE_LEGEND})", line)
        values = _raw("common", "script_values", "sr_launch_windows_generated.txt")
        for code, body in enumerate(glw.BODIES, start=1):
            self.assertIn(f"sr_window_body_code_{body.key} = {{ value = {code} }}", values)

    def test_the_console_names_the_body_it_copied(self):
        console = _raw(*self.FILES[1])
        pairs = re.findall(r'sr_window_log_copy = \{ BODY = (\w+) \}\s*debug_log = "TE_LAUNCH_WINDOWS (\w+) ', console)
        self.assertEqual([a for a, _ in pairs], [b.key for b in glw.BODIES])
        for copied, named in pairs:
            self.assertEqual(copied, named)

    def test_every_global_a_line_reads_is_copied(self):
        copy = _block(_strip(_raw(*self.FILES[0])), "sr_window_log_copy")
        copied = set(re.findall(r"name = (sr_window_log_\w+_now)", copy))
        for parts in self.FILES:
            for name in re.findall(r"GetGlobalVariable\('(sr_window_log_\w+_now)'\)", _raw(*parts)):
                with self.subTest(file=parts[-1], name=name):
                    self.assertIn(name, copied)


class TransitTest(unittest.TestCase):
    """Transit times by drive (solar colonization slices 2-3 design § 2): the chemical era's Hohmann times,
    fusion faster with windows still mattering, the torch months to the outer planets; and the script
    reads every table back for every month."""

    # The scope's minimum-energy times (§ 5.3), in months: "about 4 months to Mercury, 5 to Venus, 8 to 9
    # to Mars, 15 to Ceres, 2.7 years to Jupiter, 6 to Saturn, 16 to Uranus, 31 to Neptune and 45 to Pluto".
    # Pluto is past its mean distance for most of the span, so its median transfer runs longer.
    CHEMICAL = {"mercury": (3, 5), "venus": (4, 6), "mars": (8, 10), "ceres": (14, 17), "jupiter": (30, 36),
                "saturn": (68, 78), "uranus": (180, 200), "neptune": (355, 380), "kuiper": (480, 660)}

    def test_chemical_is_the_scope_s_hohmann_times(self):
        chemical = {p.body.key: p.transit["chemical"][0] for p in plans()[0]}
        chemical.update({t.body.key: t.transit["chemical"] for t in glw.plan_transit_all()})
        for key, (lo, hi) in self.CHEMICAL.items():
            with self.subTest(body=key):
                self.assertGreaterEqual(chemical[key], lo)
                self.assertLessEqual(chemical[key], hi)
        for p in plans()[0]:
            self.assertEqual(set(p.transit["chemical"].values()), {glw.months_of(p.hohmann_days)}, p.body.key)

    def test_a_better_drive_is_never_slower_and_each_is_at_least_a_month(self):
        keys = [d.key for d in glw.DRIVES]
        for p in plans()[0]:
            for off in p.transit["chemical"]:
                months = [p.transit[k][off] for k in keys]
                with self.subTest(body=p.body.key, offset=off):
                    self.assertEqual(months, sorted(months, reverse=True))
                    self.assertGreaterEqual(min(months), 1)
        for t in glw.plan_transit_all():
            months = [t.transit[k] for k in keys]
            self.assertEqual(months, sorted(months, reverse=True))

    def test_fusion_is_well_under_hohmann_in_a_window_and_the_torch_takes_months(self):
        for p in plans()[0]:
            with self.subTest(body=p.body.key):
                window = [p.transit["fusion"][o] for o in (-1, 0, 1)]
                self.assertLess(max(window), p.transit["chemical"][0])
                if p.body.key in ("jupiter", "saturn", "uranus", "neptune", "kuiper"):
                    self.assertLess(max(window), p.transit["chemical"][0] * 0.6)
                self.assertLessEqual(max(p.transit["torch"].values()), 14)
                self.assertLessEqual(max(p.transit["antimatter"].values()), 5)
        # Windows still matter for fusion to the far worlds: off-window is slower.
        for key in ("saturn", "uranus", "neptune"):
            p = plan(key)
            far = max(p.transit["fusion"][o] for o in p.transit["fusion"] if abs(o) >= 4)
            self.assertGreater(far, 2 * p.transit["fusion"][0], key)

    def test_the_script_reads_back_every_transit_table_every_month(self):
        interp = interpreter()
        _, first, last = plans()
        for p in plans()[0]:
            key = p.body.key
            optima = [w.optimum_month for w in p.windows]
            with self.subTest(body=key):
                self.assertEqual(interp.value(f"sr_transit_chemical_{key}", first), p.transit["chemical"][0])
                for month in range(first, last + 1, 7):
                    nxt = next(o for o in optima if o + 1 >= month)
                    prev = max((o for o in optima if o < nxt), default=None)
                    nearest = prev if prev is not None and month - prev <= nxt - month else nxt
                    for drive in glw.DRIVES[1:]:
                        self.assertEqual(interp.value(f"sr_transit_{drive.key}_{key}", month),
                                         p.transit[drive.key][month - nearest], (drive.key, month))
        for t in glw.plan_transit_all():
            for drive in glw.DRIVES:
                self.assertEqual(interp.value(f"sr_transit_{drive.key}_{t.body.key}", first), t.transit[drive.key])

    def test_the_cache_holds_each_drive_and_the_reader_picks_by_drive_level(self):
        windows = _strip(_raw("common", "scripted_effects", "sr_launch_window_effects.txt"))
        cache = _block(windows, "sr_launch_window_cache_body")
        for drive in glw.DRIVES[1:]:
            self.assertIn(f"set_global_variable = {{ name = sr_window_transit_{drive.key}_$BODY$ "
                          f"value = sr_transit_{drive.key}_$BODY$ }}", cache)
        values = _strip(_raw("common", "script_values", "sr_launch_windows_generated.txt"))
        for b in list(glw.BODIES) + list(glw.TRANSIT_ONLY):
            reader = _block(values, f"sr_transit_months_{b.key}")
            with self.subTest(body=b.key):
                self.assertIn(f"value = sr_transit_chemical_{b.key}", reader)
                self.assertEqual(re.findall(r"sr_drive_level >= (\d)", reader), ["3", "2", "1"])
        level = _block(_strip(_raw("common", "script_values", "sr_launch_window_values.txt")), "sr_drive_level")
        for tech in ("compact_fusion_reactors", "fusion_power"):
            self.assertIn(f"has_technology_researched = {tech}", level)
        self.assertIn("sr_launch_has_antimatter = yes", level)
        triggers = _strip(_raw("common", "scripted_triggers", "sr_launch_window_triggers.txt"))
        self.assertIn("sr_launch_has_antimatter = yes", _block(triggers, "sr_launch_has_fusion"))
        self.assertIn("building_antimatter_facility", _block(triggers, "sr_launch_has_antimatter"))

    def test_a_targeted_departure_weighs_its_own_body_s_wait(self):
        triggers = _strip(_raw("common", "scripted_triggers", "sr_launch_window_triggers.txt"))
        paid = _block(triggers, "sr_launch_target_departs_paid")
        self.assertIn("sr_launch_months_cost_$BODY$ <= sr_launch_target_months_allowed_$BODY$", paid)
        values = _strip(_raw("common", "script_values", "sr_launch_windows_generated.txt"))
        for b in glw.BODIES:
            allowed = _block(values, f"sr_launch_target_months_allowed_{b.key}")
            self.assertIn(f"value = sr_window_wait_months_{b.key}", allowed)
            cost = _block(values, f"sr_launch_target_cost_{b.key}")
            self.assertIn(f"sr_launch_target_departs_paid = {{ BODY = {b.key} }}", cost)


_LEGS = None


def legs():
    global _LEGS
    if _LEGS is None:
        _LEGS = glw.plan_legs()
    return _LEGS


def legs_interpreter():
    values = parse_file(_raw("common", "script_values", "sr_launch_windows_generated.txt"))
    values.update(parse_file(_raw("common", "script_values", "sr_fleet_legs_generated.txt")))
    triggers = parse_file(_raw("common", "scripted_triggers", "sr_launch_windows_generated.txt"))
    return Interpreter(values, triggers)


class FleetLegsTest(unittest.TestCase):
    """The fleets' legs between the nine locations (solar colonization slice 6 design § 1.2): every
    ordered pair and drive has its readers; a better drive is never slower; Earth's outbound months are
    the colony fleets' transit; the script's mean-cycle phase is the generator's for every month."""

    @classmethod
    def setUpClass(cls):
        cls.text = _strip(_raw("common", "script_values", "sr_fleet_legs_generated.txt"))
        cls.names = set(re.findall(r"(?m)^(sr_leg_\w+) = \{", cls.text))

    def test_nine_locations_and_every_ordered_pair_by_kind(self):
        self.assertEqual([loc.key for loc in glw.LOCATIONS],
                         ["earth", "inner", "mars", "asteroids", "jupiter", "saturn", "uranus", "neptune", "kuiper"])
        self.assertEqual([loc.code for loc in glw.LOCATIONS], list(range(1, 10)))
        self.assertEqual({loc.key: loc.body for loc in glw.LOCATIONS}["inner"], "venus")
        self.assertEqual({loc.key: loc.body for loc in glw.LOCATIONS}["asteroids"], "ceres")
        kinds = [k for _, _, k in glw.LEGS]
        self.assertEqual(len(glw.LEGS), 72)
        self.assertEqual(kinds.count("exact"), 8)
        self.assertEqual(kinds.count("cycle"), 8 + 12)  # every return, and the inner four's 12 ordered pairs
        self.assertEqual(kinds.count("fixed"), 44)

    def test_every_ordered_pair_and_drive_has_both_readers(self):
        for a, b, _ in glw.LEGS:
            for drive in glw.DRIVES:
                for name in ("months", "dv", "months_rapid", "dv_rapid"):
                    stem, rapid = (name.split("_") + [""])[:2]
                    reader = f"sr_leg_{stem}_{'rapid_' if rapid else ''}{drive.key}_{a}_{b}"
                    with self.subTest(reader=reader):
                        self.assertIn(reader, self.names)

    def test_a_better_drive_is_never_slower(self):
        keys = [d.key for d in glw.DRIVES]
        for p in legs():
            for off in p.months["chemical"]:
                months = [p.months[k][off] for k in keys]
                with self.subTest(leg=(p.a, p.b), offset=off):
                    self.assertEqual(months, sorted(months, reverse=True))
                    self.assertGreaterEqual(min(months), 1)

    def test_earth_s_outbound_months_are_the_colony_fleets_transit(self):
        bodies = {p.body.key: p for p in plans()[0]}
        for p in legs():
            if p.kind != "exact":
                continue
            body = glw.LOCATION[p.b].body
            for drive in glw.DRIVES:
                with self.subTest(leg=p.b, drive=drive.key):
                    self.assertEqual(p.months[drive.key], bodies[body].transit[drive.key])
                    self.assertEqual(_block(self.text, f"sr_leg_months_{drive.key}_earth_{p.b}").strip(),
                                     f"value = sr_transit_{drive.key}_{body}")
                    if len({glw._dv_text(drive, v) for v in p.dv[drive.key].values()}) > 1:
                        self.assertIn(f"sr_launch_offset_{body}",
                                      _block(self.text, f"sr_leg_dv_{drive.key}_earth_{p.b}"))

    def test_the_phase_is_integer_arithmetic_on_a_positive_dividend(self):
        game_start = glw.month_index(1836, 1)
        _, _, last = plans()
        for p in legs():
            if p.kind != "cycle":
                continue
            with self.subTest(leg=(p.a, p.b)):
                self.assertGreaterEqual(100 * (game_start - glw.LEG_BASE_MONTH) + p.epoch, 0)
                self.assertLess(100 * (last - glw.LEG_BASE_MONTH) + p.epoch, 2_000_000)
                self.assertTrue(0 <= p.epoch < p.cycle)
                for phase in range(p.cycle):
                    folded = glw.fold_phase(phase, p.cycle)
                    self.assertTrue(-p.cycle / 2 <= folded < p.cycle / 2)

    def test_the_script_reads_back_every_leg_every_month(self):
        interp = legs_interpreter()
        _, first, last = plans()
        bodies = {p.body.key: p for p in plans()[0]}
        for p in legs():
            with self.subTest(leg=(p.a, p.b)):
                if p.kind == "fixed":
                    for drive in glw.DRIVES:
                        self.assertEqual(interp.value(f"sr_leg_months_{drive.key}_{p.a}_{p.b}", first),
                                         p.months[drive.key][0])
                    continue
                for month in range(first, last + 1, 1 if p.kind == "cycle" else 5):
                    if p.kind == "cycle":
                        phase = interp.value(f"sr_leg_phase_{p.a}_{p.b}", month)
                        self.assertEqual(phase, glw.leg_phase(month, p.epoch, p.cycle), month)
                        off = glw.leg_offset(month, p.epoch, p.cycle)
                    else:
                        off = interp.value(f"sr_launch_offset_{glw.LOCATION[p.b].body}", month)
                    for drive in glw.DRIVES:
                        months = interp.value(f"sr_leg_months_{drive.key}_{p.a}_{p.b}", month)
                        dv = interp.value(f"sr_leg_dv_{drive.key}_{p.a}_{p.b}", month)
                        self.assertEqual(months, p.months[drive.key][off], (drive.key, month))
                        self.assertAlmostEqual(dv, float(glw._dv_text(drive, p.dv[drive.key][off])), places=6,
                                               msg=(drive.key, month))
                    rapid = interp.value(f"sr_leg_months_rapid_antimatter_{p.a}_{p.b}", month)
                    self.assertEqual(rapid, max(1, math.ceil(0.75 * p.months["antimatter"][off])), month)
        self.assertTrue(bodies)

    def test_rapid_response_flies_one_drive_ahead(self):
        for a, b, _ in glw.LEGS:
            for i, drive in enumerate(glw.DRIVES[:-1]):
                ahead = glw.DRIVES[i + 1].key
                with self.subTest(leg=(a, b), drive=drive.key):
                    self.assertEqual(_block(self.text, f"sr_leg_months_rapid_{drive.key}_{a}_{b}").strip(),
                                     f"value = sr_leg_months_{ahead}_{a}_{b}")
                    self.assertEqual(_block(self.text, f"sr_leg_dv_rapid_{drive.key}_{a}_{b}").strip(),
                                     f"value = sr_leg_dv_{ahead}_{a}_{b}")

    def test_the_fixed_legs_medians_lie_in_their_sampled_range(self):
        for p in legs():
            if p.kind != "fixed":
                continue
            for drive in glw.DRIVES:
                m_lo, m_hi, dv_lo, dv_hi = p.sampled_range[drive.key]
                with self.subTest(leg=(p.a, p.b), drive=drive.key):
                    self.assertLessEqual(p.months[drive.key][0], m_hi)
                    self.assertGreaterEqual(p.dv[drive.key][0], dv_lo - 1e-9)
                    self.assertLessEqual(p.dv[drive.key][0], dv_hi + 1e-9)
                    if drive.key == "chemical":
                        self.assertGreaterEqual(p.months[drive.key][0], m_lo)

    def test_a_planet_s_capture_orbit_by_hand(self):
        # Mars: GM 42,828.37 km^3/s^2, periapsis a tenth of its 3,389.5 km radius up, e = 0.9. At an
        # excess speed of 2.65 km/s the hyperbola's periapsis speed is sqrt(2.65^2 + 2 GM / rp) = 5.4773
        # and the capture orbit's sqrt(GM (1 + e) / rp) = 4.6722: 0.805 km/s either way.
        self.assertAlmostEqual(float(glw.system_dv("mars", 2.65)), 0.805, places=3)
        self.assertEqual(float(glw.system_dv("ceres", 2.65)), 2.65)  # a rendezvous
        self.assertAlmostEqual(float(glw.parking_dv(2.94)), 3.6, places=1)  # Earth to Mars, the textbook 3.6

    def test_the_chemical_drive_s_reach(self):
        """Design § 2: 12 km/s is a round trip to Mars or Venus, one way to Jupiter."""
        by = {(p.a, p.b): p for p in legs()}
        trip = lambda a, b: by[(a, b)].dv["chemical"][0]  # noqa: E731
        self.assertLess(trip("earth", "mars") + trip("mars", "earth"), 12)
        self.assertLess(trip("earth", "inner") + trip("inner", "earth"), 12)
        self.assertLess(trip("earth", "jupiter"), 12)
        self.assertGreater(trip("earth", "jupiter") + trip("jupiter", "earth"), 12)

    def test_the_file_stays_a_sane_size(self):
        lines = _raw("common", "script_values", "sr_fleet_legs_generated.txt").count("\n")
        self.assertLess(lines, 15_000)


class StagedBankTest(unittest.TestCase):
    """A programme with no colony restarts its bar when it stops (its entry fails, deactivates or runs
    `immediate` again); the whole fleets it had staged are kept apart and come back (review L2)."""

    @classmethod
    def setUpClass(cls):
        cls.windows = _strip(_raw("common", "scripted_effects", "sr_launch_window_effects.txt"))
        je = _strip(_raw("common", "journal_entries", "je_space_race.txt"))
        cls.entry = _block(je, "je_space_race_solar_colonization")

    def test_every_stop_banks_before_it_clears(self):
        immediate = _block(self.entry, "\timmediate")
        self.assertLess(immediate.index("sr_launch_bank_staged_fleets = yes"),
                        immediate.index("set_variable = { name = sr_progress_solar_colonization value = 0 }"))
        on_fail = _block(self.entry, "\ton_fail")
        self.assertLess(on_fail.index("sr_launch_bank_staged_fleets = yes"),
                        on_fail.index("sr_cleanup_milestone_variables_effect = { MILESTONE = solar_colonization }"))
        effects = _strip(_raw("common", "scripted_effects", "space_race_effects.txt"))
        cleanup = _block(effects, "sr_cleanup_inactive_space_race_milestones")
        self.assertLess(cleanup.index("sr_launch_bank_staged_fleets = yes"),
                        cleanup.index("sr_cleanup_milestone_if_inactive_base = { MILESTONE = solar_colonization }"))

    def test_the_launch_month_restores_first(self):
        month = _block(self.windows, "sr_launch_month")
        self.assertLess(month.index("sr_launch_restore_banked_fleets = yes"), month.index("sr_launch_fleet_ready"))

    def test_banking_keeps_whole_fleets_and_adds_up(self):
        bank = _block(self.windows, "sr_launch_bank_staged_fleets")
        self.assertIn("sr_launch_staged_whole_fleets >= 1", bank)
        self.assertIn("NOT = { has_global_variable = sr_all_colonies_complete }", bank)
        self.assertIn("change_variable = { name = sr_launch_banked_fleets add = sr_launch_staged_whole_fleets }", bank)
        self.assertNotIn("set_variable = { name = sr_launch_banked_fleets value = sr_", bank)
        values = _strip(_raw("common", "script_values", "sr_launch_window_values.txt"))
        whole = _block(values, "sr_launch_staged_whole_fleets")
        self.assertEqual(re.findall(r"(value|divide|floor) = (\S+)", whole),
                         [("value", "sr_progress_solar_colonization_value"), ("divide", "sr_solar_colonization_goal"),
                          ("floor", "yes")])
        restore = _block(self.windows, "sr_launch_restore_banked_fleets")
        self.assertIn("change_local_variable = { name = sr_launch_restored multiply = sr_solar_colonization_goal }", restore)
        self.assertIn("remove_variable = sr_launch_banked_fleets", restore)


if __name__ == "__main__":
    unittest.main()
