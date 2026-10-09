"""Demographics phase 1 wiring (docs/superpowers/plans/2026-10-08-demographics-phases-0-1.md).

Static checks on the script: the rule's settings and wrappers, guarded divisions, the
pulse wiring, the gates around every cohort entry point. Later tasks add tests here.
"""

import itertools
import random
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model  # noqa: E402
import organize_loc  # noqa: E402

RULES = ROOT / "common" / "game_rules" / "extra_game_rules.txt"
TRIGGERS = ROOT / "common" / "scripted_triggers" / "te_demog_triggers.txt"
EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_effects.txt"
INH_EFFECTS = ROOT / "common" / "scripted_effects" / "te_inheritance_effects.txt"
INH_VALUES = ROOT / "common" / "script_values" / "te_inheritance_values.txt"
INH_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_inheritance_on_actions.txt"
DEMOG_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_demog_on_actions.txt"
WEALTH_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_wealth_effects.txt"
GENERATED_VALUES = ROOT / "common" / "script_values" / "te_demog_generated_values.txt"
DEMOG_FILES = sorted(p for d in ("common", "events") for p in (ROOT / d).rglob("te_demog*.txt"))


def _text(path):
    return Path(path).read_text(encoding="utf-8-sig")


def _block(text, name):
    """The body of the top-level `name = { ... }`, by brace counting."""
    m = re.search(rf"^{re.escape(name)} = \{{", text, re.M)
    if not m:
        raise AssertionError(f"{name} not found")
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class TestRule(unittest.TestCase):
    def test_three_settings_default_full(self):
        body = _block(_text(RULES), "demographics_rule")
        self.assertIn("default = demographics_full", body)
        for setting in ("demographics_full", "demographics_display_only", "demographics_disabled"):
            self.assertIn(f"{setting} = {{", body)

    def test_wrappers_test_negatively(self):
        text = _text(TRIGGERS)
        self.assertIn("NOT = { has_game_rule = demographics_disabled }", _block(text, "te_demog_cohorts_run"))
        effects = _block(text, "te_demog_effects_run")
        self.assertIn("te_demog_cohorts_run = yes", effects)
        self.assertIn("NOT = { has_game_rule = demographics_display_only }", effects)

    def test_nothing_tests_full(self):
        for path in [*ROOT.glob("common/**/*.txt"), *ROOT.glob("events/*.txt")]:
            self.assertNotIn("has_game_rule = demographics_full", _text(path), str(path))


class TestDivisions(unittest.TestCase):
    def test_every_division_is_guarded(self):
        """A divide takes a literal or a value block with a floor (Review Focus 2)."""
        for path in DEMOG_FILES:
            text = _text(path)
            for m in re.finditer(r"divide = (\S+)", text):
                arg = m.group(1)
                if re.fullmatch(r"-?\d+(\.\d+)?", arg) or arg.startswith("$"):
                    continue
                self.assertEqual(arg, "{", f"{path.name}: unguarded divide = {arg}")
                body = text[m.end():text.index("}", m.end())]
                self.assertIn("min =", body, f"{path.name}: divide block without min near {m.start()}")


class TestLoc(unittest.TestCase):
    def test_demog_keys_file_together(self):
        for key in ("te_demog_tab", "te_demog_pyramid_tt", "te_demog_wc_desc", "te_demog_label_add"):
            self.assertEqual(organize_loc.categorize_key(key, set()), "MISCELLANEOUS", key)


class TestWalks(unittest.TestCase):
    def test_one_pop_walk_and_one_building_walk(self):
        body = _block(_text(EFFECTS), "te_demog_walks")
        self.assertEqual(body.count("every_scope_pop"), 1)
        self.assertEqual(body.count("every_scope_building"), 1)

    def test_inheritance_reads_the_walk(self):
        self.assertNotIn("te_inh_agrarian_share_value", _text(INH_VALUES))
        self.assertIn("value = var:te_dg_agr_share", _block(_text(INH_EFFECTS), "te_inh_refresh_rural_effects"))
        self.assertNotIn("on_yearly_pulse_state", _text(INH_ON_ACTIONS))

    def test_orchestrator_walks_then_refreshes_inheritance(self):
        body = _block(_text(EFFECTS), "te_demog_state_yearly")
        self.assertLess(body.index("te_demog_walks = yes"), body.index("te_inh_refresh_rural_effects = yes"))

    def test_state_pulse_is_not_gated_by_the_rule(self):
        hook = _block(_text(DEMOG_ON_ACTIONS), "te_demog_state_yearly_on_action")
        self.assertNotIn("te_demog_cohorts_run", hook)


def _parse_script(text):
    """Paradox script as an ordered tree: a list of (key, operator, value), value a str or a list."""
    text = re.sub(r"#[^\n]*", "", text)
    tokens = re.findall(r"[{}]|[<>]=?|=|[^\s{}=<>]+", text)
    pos = 0

    def block():
        nonlocal pos
        items = []
        while pos < len(tokens) and tokens[pos] != "}":
            key, op = tokens[pos], tokens[pos + 1]
            pos += 2
            if tokens[pos] == "{":
                pos += 1
                value = block()
                pos += 1
            else:
                value = tokens[pos]
                pos += 1
            items.append((key, op, value))
        return items

    return block()


def _find(items, key):
    return next(v for k, _, v in items if k == key)


class _Interp:
    """Just enough of the engine to run te_demog_state_gini: locals, variables, if, value blocks."""

    def __init__(self, variables, constants):
        self.vars, self.locals, self.constants = dict(variables), {}, constants

    def number(self, tok):
        if tok.startswith("local_var:"):
            return self.locals[tok[10:]]
        if tok.startswith("var:"):
            return self.vars[tok[4:]]
        if tok in self.constants:
            return self.constants[tok]
        return float(tok)

    def value(self, v):
        if isinstance(v, str):
            return self.number(v)
        acc = 0.0
        lo, hi = None, None
        for k, _, arg in v:
            if k == "value":
                acc = self.value(arg)
            elif k == "add":
                acc += self.value(arg)
            elif k == "subtract":
                acc -= self.value(arg)
            elif k == "multiply":
                acc *= self.value(arg)
            elif k == "divide":
                acc /= self.value(arg)
            elif k == "min":
                lo = self.value(arg)
            elif k == "max":
                hi = self.value(arg)
            else:
                raise AssertionError(f"value operator {k}")
        if lo is not None:
            acc = max(acc, lo)
        if hi is not None:
            acc = min(acc, hi)
        return acc

    def holds(self, limit):
        ops = {">": float.__gt__, ">=": float.__ge__, "<": float.__lt__, "<=": float.__le__}
        return all(ops[op](self.number(k), self.number(v)) for k, op, v in limit)

    def run(self, items):
        for key, _, val in items:
            if key == "if":
                if self.holds(_find(val, "limit")):
                    self.run([i for i in val if i[0] != "limit"])
            elif key in ("set_local_variable", "set_variable"):
                target = self.locals if key == "set_local_variable" else self.vars
                target[_find(val, "name")] = self.value(_find(val, "value"))
            else:
                raise AssertionError(f"effect {key}")


class TestStateGini(unittest.TestCase):
    """te_demog_state_gini against demographics_model.grouped_gini, run through a mini interpreter."""

    @classmethod
    def setUpClass(cls):
        cls.effect = _find(_parse_script(_text(WEALTH_EFFECTS)), "te_demog_state_gini")
        constants = {k: float(_find(v, "value")) for k, _, v in _parse_script(_text(GENERATED_VALUES))
                     if k in ("te_demog_k_gini_floor", "te_demog_k_gini_scale")}
        cls.constants = constants

    def shown(self, groups):
        names = ("lo", "mi", "up")
        variables = {}
        for name, (n, y) in zip(names, groups):
            variables[f"te_dg_n_{name}"], variables[f"te_dg_y_{name}"] = float(n), float(y)
        interp = _Interp(variables, self.constants)
        interp.run(self.effect)
        return interp.vars["te_dg_gini"]

    def test_matches_the_model_in_every_order(self):
        # (people, income) for lower, middle, upper: in order, and each other order of per-head incomes
        base = [(900, 1800), (300, 1500), (40, 900)]
        for perm in itertools.permutations(base):
            expected = demographics_model.shown_gini(demographics_model.grouped_gini(list(perm)))
            self.assertAlmostEqual(self.shown(perm), expected, places=9, msg=str(perm))

    def test_matches_the_model_on_random_states(self):
        rng = random.Random(7)
        for _ in range(300):
            groups = []
            for _ in range(3):
                n = rng.choice([0, rng.randint(1, 50000)])
                groups.append((n, n * rng.uniform(0, 40)))
            expected = demographics_model.shown_gini(demographics_model.grouped_gini(groups))
            self.assertAlmostEqual(self.shown(groups), expected, places=9, msg=str(groups))

    def test_no_people_or_no_income_is_the_floor(self):
        floor = self.constants["te_demog_k_gini_floor"]
        self.assertAlmostEqual(self.shown([(0, 0), (0, 0), (0, 0)]), floor)
        self.assertAlmostEqual(self.shown([(10, 0), (5, 0), (1, 0)]), floor)

    def test_one_stratum_is_equal(self):
        self.assertAlmostEqual(self.shown([(0, 0), (500, 1234), (0, 0)]), self.constants["te_demog_k_gini_floor"])
