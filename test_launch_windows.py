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
        cls.colony = _block(cls.effects, "sr_establish_colony_effect")
        cls.site_body = {site: b.key for b in glw.BODIES for site in b.sites}

    def test_every_colony_site_is_drawn_through_its_window_body(self):
        branches = re.findall(r"trigger = \{(.*?)\}\s*set_global_variable = \{ name = sr_colony_(\w+) value = yes \}(.*?)"
                              r"trigger_event", self.colony, re.S)
        sites = {site for _, site, _ in branches}
        self.assertEqual(sites, set(self.site_body) | set(glw.UNGATED_SITES))
        self.assertEqual(len(branches), 34)
        for trigger, site, effect in branches:
            with self.subTest(site=site):
                self.assertIn(f"NOT = {{ has_global_variable = sr_colony_{site} }}", trigger)
                if site in glw.UNGATED_SITES:
                    self.assertIn("sr_launch_mercury_departs = yes", trigger)
                    self.assertNotIn("sr_launch_window_gate_check", effect)
                else:
                    body = self.site_body[site]
                    self.assertEqual(re.findall(r"sr_launch_site_departs = \{ BODY = (\w+) \}", trigger), [body])
                    self.assertEqual(re.findall(r"sr_launch_window_gate_check = \{ BODY = (\w+) \}", effect), [body])

    def test_each_stage_holds_its_bodies_sites(self):
        draws = self.colony[:self.colony.index("change_variable = { name = sr_colony_count")]
        stages = re.split(r"global_var:sr_colonization_stage = (\d)", draws)
        for i in range(1, len(stages), 2):
            stage, body = int(stages[i]), stages[i + 1]
            drawn = set(re.findall(r"name = sr_colony_(\w+) value = yes", body))
            expected = {s for b in glw.BODIES if b.stage == stage for s in b.sites}
            expected |= {s for s, st in glw.UNGATED_SITES.items() if st == stage}
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

    def test_setback_cap_applies_to_solar_colonization_only(self):
        for name, mult in (("sr_apply_ambitious_failure_progress_loss", "0.75"),
                           ("sr_apply_safe_setback_progress_loss", "0.85")):
            body = _block(self.effects, name)
            with self.subTest(helper=name):
                self.assertIn(f"sr_apply_solar_colonization_progress_loss = {{ MULT = {mult} }}", body)
                self.assertEqual(len(re.findall(rf"sr_apply_progress_loss_base = \{{ MILESTONE = \w+\s+MULT = {mult} \}}",
                                                body)), 7)
        self.assertNotIn("MILESTONE = solar_colonization MULT", self.effects)

    def test_setback_cap_takes_a_share_of_one_goal_at_most(self):
        # The helper's arithmetic, step by step, against loss = share x min(P, G).
        body = _block(self.windows, "sr_apply_solar_colonization_progress_loss")
        self.assertIn("var:sr_progress_solar_colonization > sr_solar_colonization_goal", body)
        steps = re.findall(r"(subtract|add|multiply) = (\S+) \}", body)
        self.assertEqual(steps, [("multiply", "$MULT$"), ("subtract", "sr_solar_colonization_goal"),
                                 ("add", "local_var:sr_setback_readied"), ("multiply", "$MULT$")])
        for progress in (100.0, 400.0, 1000.0):
            for mult in (0.75, 0.85):
                goal = 400.0
                after = progress - goal + goal * mult if progress > goal else progress * mult
                self.assertAlmostEqual(progress - after, (1 - mult) * min(progress, goal))

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
        lines = re.findall(r'debug_log = "(TE_SELF_CHECK [^"]*)"', effects)
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
