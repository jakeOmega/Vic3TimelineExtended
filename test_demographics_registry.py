"""Demographics phase 1 wiring (docs/superpowers/plans/2026-10-08-demographics-phases-0-1.md).

Static checks on the script: the rule's settings and wrappers, guarded divisions, the
pulse wiring, the gates around every cohort entry point. Later tasks add tests here.
"""

import dataclasses
import itertools
import math
import random
import re
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model  # noqa: E402
import demographics_params as P  # noqa: E402
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
GENERATED_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_generated_effects.txt"
VALUES = ROOT / "common" / "script_values" / "te_demog_values.txt"
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


class TestStep(unittest.TestCase):
    def test_orchestrator_branches(self):
        """Seed when there is no census, a gap of more than a year or an emptied ring;
        step once a year; nothing on a second pulse in the same year (Review Focus 3)."""
        body = _block(_text(EFFECTS), "te_demog_state_yearly")
        self.assertIn("te_demog_cohorts_run = yes", body)
        self.assertIn("te_demog_seed = yes", body)
        self.assertIn("te_demog_step = yes", body)
        self.assertIn("te_demog_year_gap > 1", body)
        self.assertIn("te_demog_year_gap = 1", body)

    def test_every_cohort_entry_point_is_gated(self):
        """Review Focus 5: nothing writes a cohort without te_demog_cohorts_run."""
        text = _text(EFFECTS)
        for caller in ("te_demog_state_yearly", "te_demog_country_game_start"):
            body = _block(text, caller)
            for entry in ("te_demog_seed = yes", "te_demog_step = yes"):
                if entry in body:
                    gate = body.rfind("te_demog_cohorts_run = yes", 0, body.index(entry))
                    self.assertNotEqual(gate, -1, f"{caller}: {entry} before the gate")

    def test_family_limitation_matches_the_params(self):
        modifiers = _text(ROOT / "common" / "static_modifiers" / "te_demog_modifiers.txt")
        body = _block(modifiers, "te_demog_family_limitation")
        self.assertIn(f"country_fertility_means_add = {P.FAMILY_LIMITATION_MEANS}", body)
        self.assertIn("name = te_demog_family_limitation", _text(ROOT / "common" / "history" / "extra_history.txt"))

    def test_fold_writes_the_births(self):
        body = _block(_text(EFFECTS), "te_demog_fold_slot")
        self.assertIn("name = te_dg_f$S$", body)
        self.assertIn("local_var:te_dg_births", body)

    def test_empty_ages_stay_empty(self):
        text = _text(EFFECTS)
        self.assertIn("remove_variable = te_dg_f$S$", _block(text, "te_demog_seed_slot"))
        self.assertIn("remove_variable = te_dg_f$S$", _block(text, "te_demog_age_slot"))

    def test_slot_skips_empty_slots_but_keeps_counting_ages(self):
        body = _block(_text(EFFECTS), "te_demog_slot")
        self.assertIn("has_variable = te_dg_f$S$", body)
        self.assertGreater(body.index("change_local_variable = { name = te_dg_age add = 1 }"),
                           body.index("has_variable = te_dg_f$S$"))


def _raw_blocks(paths):
    """name -> body text of every top-level `name = { ... }` in the files, comments removed."""
    out = {}
    for path in paths:
        text = re.sub(r"#[^\n]*", "", _text(path))
        for m in re.finditer(r"^([\w.]+) = \{", text, re.M):
            depth, i = 1, m.end()
            while depth:
                depth += {"{": 1, "}": -1}.get(text[i], 0)
                i += 1
            out[m.group(1)] = text[m.end():i - 1]
    return out


class _Engine:
    """Enough of the engine to run the census: value blocks applied in order (min and max clamp
    where they stand), variables and locals, if / else_if / else, while, triggers, and scripted
    effects with their $ARG$ substituted as text. A read of a variable or local that was never
    set fails, as does an argument the callee doesn't name (the script_argument_audit rule).
    `fixtures` stand in for engine reads and for script values that read the owner."""

    def __init__(self, fixtures, triggers=None, effects=None):
        self.effects = _raw_blocks([EFFECTS, GENERATED_EFFECTS])
        self.effects.update(effects or {})
        self.values = _raw_blocks([VALUES, GENERATED_VALUES])
        self.triggers = _raw_blocks([TRIGGERS])
        self.trigger_fixtures = dict(triggers or {})
        self.fixtures = dict(fixtures)
        self.vars, self.locals, self._trees = {}, {}, {}

    def _tree(self, table, name, args=()):
        key = (id(table), name, args)
        if key not in self._trees:
            text = table[name]
            for k, v in args:
                assert isinstance(v, str), f"{name}: block argument {k}"
                assert f"${k}$" in text, f"{name}: unused argument {k}"
                text = text.replace(f"${k}$", v)
            assert "$" not in text, f"{name}: argument left unbound"
            self._trees[key] = _parse_script(text)
        return self._trees[key]

    def number(self, tok):
        if tok.startswith("local_var:"):
            assert tok[10:] in self.locals, f"read of unset local {tok}"
            return self.locals[tok[10:]]
        if tok.startswith("var:"):
            assert tok[4:] in self.vars, f"read of missing variable {tok}"
            return self.vars[tok[4:]]
        if tok in self.fixtures:
            return self.fixtures[tok]
        if tok in self.values:
            return self.value(self._tree(self.values, tok))
        return float(tok)

    def value(self, v):
        return self.number(v) if isinstance(v, str) else self._ops(v, 0.0)

    def _ops(self, items, acc):
        chain = None
        for key, _, arg in items:
            if key in ("if", "else_if", "else"):
                go, chain = self._branch(key, arg, chain)
                if go:
                    acc = self._ops([i for i in arg if i[0] != "limit"], acc)
                continue
            chain = None
            if key == "value":
                acc = self.value(arg)
            elif key == "add":
                acc += self.value(arg)
            elif key == "subtract":
                acc -= self.value(arg)
            elif key == "multiply":
                acc *= self.value(arg)
            elif key == "divide":
                d = self.value(arg)
                assert d != 0, "division by zero"
                acc /= d
            elif key == "min":
                acc = max(acc, self.value(arg))
            elif key == "max":
                acc = min(acc, self.value(arg))
            elif key == "floor":
                acc = float(math.floor(acc))
            elif key == "modulo":
                acc = math.fmod(acc, self.value(arg))
            else:
                raise AssertionError(f"value operator {key}")
        return acc

    def _branch(self, key, block, chain):
        """(run this branch, the chain after it); chain None = closed, True = a branch ran, False = open."""
        if key == "if":
            taken = self.holds(_find(block, "limit"))
            return taken, taken
        assert chain is not None, f"{key} without an if"
        if chain:
            return False, True
        if key == "else":
            return True, None
        taken = self.holds(_find(block, "limit"))
        return taken, taken

    def holds(self, items):
        return all(self._test(*item) for item in items)

    def _test(self, key, op, arg):
        if key == "NOT":
            assert len(arg) == 1, "NOT with several triggers"
            return not self.holds(arg)
        if key == "OR":
            return any(self._test(*item) for item in arg)
        if key == "AND":
            return self.holds(arg)
        if key == "has_variable":
            return arg in self.vars
        if key == "always":
            return arg == "yes"
        if key in self.trigger_fixtures:
            return self.trigger_fixtures[key] == (arg == "yes")
        if key in self.triggers:
            return self.holds(self._tree(self.triggers, key)) == (arg == "yes")
        a, b = self.value(key), self.value(arg)
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "=": a == b}[op]

    def run(self, items):
        chain = None
        for key, _, arg in items:
            if key in ("if", "else_if", "else"):
                go, chain = self._branch(key, arg, chain)
                if go:
                    self.run([i for i in arg if i[0] != "limit"])
                continue
            chain = None
            if key in ("set_local_variable", "set_variable"):
                store = self.locals if key == "set_local_variable" else self.vars
                store[_find(arg, "name")] = self.value(_find(arg, "value"))
            elif key in ("change_local_variable", "change_variable"):
                store = self.locals if key == "change_local_variable" else self.vars
                name = _find(arg, "name")
                assert name in store, f"change of unset {name}"
                store[name] = self._ops([i for i in arg if i[0] != "name"], store[name])
            elif key == "remove_variable":
                self.vars.pop(arg, None)
            elif key == "while":
                for _ in range(int(self.value(_find(arg, "count")))):
                    self.run([i for i in arg if i[0] != "count"])
            elif key in self.effects:
                args = () if arg == "yes" else tuple((k, v) for k, _, v in arg)
                self.run(self._tree(self.effects, key, args))
            else:
                raise AssertionError(f"effect {key}")

    def call(self, effect):
        self.run(_parse_script(f"{effect} = yes"))


def _engine_for(inp, year, pop, effects=None):
    """A state with the census on, the walk's sums set from `inp`, and the owner's multipliers
    (script values that read the owner's techs and laws) taken from the model."""
    mult = demographics_model.cause_multipliers(inp)
    fixtures = {
        "year": float(year),
        "state_population": float(pop),
        "te_demog_mult_infection": mult["infection"],
        "te_demog_mult_external": mult["external"],
        "te_demog_mult_chronic": mult["chronic"],
        "te_demog_mult_work": mult["work"],
        "te_demog_mult_maternal": mult["maternal"] * P.MATERNAL_PER_100K_BIRTHS,
        "te_demog_female_work_share": demographics_model.female_work_share(inp),
        "te_demog_means": demographics_model.means(inp),
    }
    eng = _Engine(fixtures, triggers={"te_demog_cohorts_run": True}, effects=effects)
    eng.vars.update(te_dg_lit=inp.literacy, te_dg_urban_share=inp.urban_share,
                    te_dg_wtfr=demographics_model.wealth_tfr(inp.sol))
    return eng


BANDS = [range(a, a + 5) for a in range(0, 85, 5)] + [range(85, P.RING_YEARS + 1)]


class TestCohortScript(unittest.TestCase):
    """te_demog_seed and te_demog_step, run through _Engine, against demographics_model's seed and step."""

    INP = demographics_model.Inputs(sol=14, literacy=0.35, urban_share=0.2, techs=frozenset({"medical_degrees"}),
                                    laws=frozenset({"law_women_in_the_fields"}))
    YEAR, POP = 1836, 250000.0

    def close(self, got, want, rel=1e-9, what=""):
        self.assertLessEqual(abs(got - want), rel * max(abs(want), 1.0), f"{what}: {got} vs {want}")

    # -- the seed -------------------------------------------------------------------------------

    def seed_both(self):
        eng = _engine_for(self.INP, self.YEAR, self.POP)
        eng.call("te_demog_seed")
        # the script reads the growth factor from a table of growth_factor; the model takes the same d
        with unittest.mock.patch.object(demographics_model, "growth_factor", lambda nrr: eng.locals["te_dg_d"]):
            ring = demographics_model.seed(self.INP, self.YEAR, self.POP)
        return eng, ring

    def test_seed_rates_match_the_model(self):
        eng, _ring = self.seed_both()
        qf, qm, mmr = demographics_model.group_rates(self.INP)
        lt_f, lt_m = demographics_model.life_table(qf), demographics_model.life_table(qm)
        e0 = (lt_f["e0"] + lt_m["e0"]) / 2
        tfr = demographics_model.fertility(self.INP, e0)["tfr"]
        self.close(eng.vars["te_dg_e0f"], lt_f["e0"], what="e0 women")
        self.close(eng.vars["te_dg_e0m"], lt_m["e0"], what="e0 men")
        self.close(eng.vars["te_dg_e0"], e0, what="e0")
        self.close(eng.vars["te_dg_e65"], (lt_f["e65"] + lt_m["e65"]) / 2, what="e65")
        self.close(eng.vars["te_dg_imr"], (qf[0] + qm[0]) / 200, what="infant mortality")
        self.close(eng.vars["te_dg_tfr"], tfr, what="TFR")
        self.close(eng.locals["te_dg_mmr"], mmr, what="maternal deaths per 100,000 births")
        nrr = demographics_model.nrr(tfr, qf)
        self.close(eng.locals["te_dg_nrr"], nrr, what="NRR")
        self.close(eng.locals["te_dg_d"], demographics_model.growth_factor(nrr), rel=1e-4, what="growth factor")

    def test_seed_ring_matches_the_model(self):
        eng, ring = self.seed_both()
        self.close(eng.vars["te_dg_scale"], 1.0, what="scale")
        self.assertEqual(eng.vars["te_dg_raw"], self.POP)
        self.assertEqual(eng.vars["te_dg_people"], self.POP)
        self.assertEqual(eng.vars["te_dg_year"], self.YEAR)
        self.assertEqual((eng.vars["te_dg_pf"], eng.vars["te_dg_pm"], eng.vars["te_dg_births"]), (0, 0, 0))
        total = 0.0
        for a, f, m in ring.by_age()[:-1]:
            k = (self.YEAR - a) % P.RING_YEARS
            if f"te_dg_f{k}" not in eng.vars:   # fewer than 1 in 100,000 newborns reach this age
                self.assertLess(f + m, 1e-5 * self.POP, f"age {a} left empty")
                continue
            self.close(eng.vars[f"te_dg_f{k}"], f, rel=1e-4, what=f"women aged {a}")
            self.close(eng.vars[f"te_dg_m{k}"], m, rel=1e-4, what=f"men aged {a}")
            total += eng.vars[f"te_dg_f{k}"] + eng.vars[f"te_dg_m{k}"]
        self.close(total, self.POP, what="the ring's people")
        for c in range(len(P.MIGRANT_CLASSES)):
            self.close(eng.vars[f"te_dg_cf{c}"], ring.class_f[c], rel=1e-4, what=f"class {c} women")
            self.close(eng.vars[f"te_dg_cm{c}"], ring.class_m[c], rel=1e-4, what=f"class {c} men")
        self.close(eng.vars["te_dg_f1840"], ring.women_18_40, rel=1e-4, what="women 18-40")
        self.close(eng.vars["te_dg_m1840"], ring.men_18_40, rel=1e-4, what="men 18-40")
        rows = ring.by_age()
        for b, ages in enumerate(BANDS):
            self.close(eng.vars[f"te_dg_bf{b}"], sum(f for a, f, _m in rows if a in ages), rel=1e-4, what=f"band {b}")
            self.close(eng.vars[f"te_dg_bm{b}"], sum(m for a, _f, m in rows if a in ages), rel=1e-4, what=f"band {b}")

    def test_seed_figures_match_the_model(self):
        eng, ring = self.seed_both()
        s = demographics_model.structure(ring)
        self.close(eng.vars["te_dg_young_share"], s["young"], rel=1e-4, what="0-14")
        self.close(eng.vars["te_dg_working_share"], s["working"], rel=1e-4, what="15-64")
        self.close(eng.vars["te_dg_old_share"], s["old"], rel=1e-4, what="65+")
        self.close(eng.vars["te_dg_dependency"], (s["young"] + s["old"]) / s["working"], rel=1e-4, what="dependency")
        self.close(eng.vars["te_dg_sex_balance"], s["men_per_100_women"], rel=1e-4, what="men per 100 women")
        self.assertLess(abs(eng.vars["te_dg_median"] - s["median"]), 0.5, "median (bands vs single years)")
        women_15_49 = sum(f for a, f, _m in ring.by_age() if 15 <= a <= 49)
        self.close(eng.vars["te_dg_w1549"], women_15_49, rel=1e-4, what="women 15-49")
        self.assertNotIn("te_dg_prev_median", eng.vars, "a first census has no previous figures")
        eng.vars["te_dg_median"] = 99.0
        eng.call("te_demog_state_figures")
        self.assertEqual(eng.vars["te_dg_prev_median"], 99.0)

    def test_reseed_clears_ages_nobody_reaches(self):
        eng = _engine_for(self.INP, self.YEAR, self.POP)
        for k in range(P.RING_YEARS):
            eng.vars[f"te_dg_f{k}"] = eng.vars[f"te_dg_m{k}"] = 1.0
        eng.call("te_demog_seed")
        oldest = (self.YEAR - 149) % P.RING_YEARS
        self.assertNotIn(f"te_dg_f{oldest}", eng.vars)
        self.assertNotIn(f"te_dg_m{oldest}", eng.vars)

    # -- the step -------------------------------------------------------------------------------

    def step_both(self, war_dead=0.0, kills=0.0, migration=0.0, stub_flows=True, scale=1.03, empty_from=None,
                  flows=None):
        """One step from the same state on both sides: the model's seed at a scale off 1, with
        people in the two oldest cohorts and in the pool. The flows reach the script one of two ways:
        stub_flows feeds war_dead, kills and migration through a te_demog_flows built from the
        model's own formulas (it tests the step alone); flows= runs the script's own te_demog_flows
        from the state's variables, against the same flows given to the model. flows is a dict:
          eb, ed (the engine's births and deaths), migration (the residual before the noise rule),
          crisis, fjob_share, techs (added to INP's), and the optional pending war (te_dg_war_in),
          kills (te_dg_kills_in) and inflow_years, left out = the variable doesn't exist.
        empty_from: nobody from that age up (the slots hold no variable; the pool keeps its people),
        the ring of the game's first decades, when the open slot is empty at the fold."""
        ring = demographics_model.seed(self.INP, self.YEAR, self.POP)
        ring.f = [x * ring.scale / scale for x in ring.f]
        ring.m = [x * ring.scale / scale for x in ring.m]
        ring.scale = scale
        folds = (self.YEAR + 1) % P.RING_YEARS          # aged 149 now, 150 at the step
        ring.f[folds], ring.m[folds] = 40.0, 25.0
        last = (self.YEAR + 2) % P.RING_YEARS           # aged 148 now: 149 after, out of the class sums
        ring.f[last], ring.m[last] = 30.0, 20.0
        if empty_from is not None:
            for a in range(empty_from, P.RING_YEARS):
                ring.f[(self.YEAR - a) % P.RING_YEARS] = ring.m[(self.YEAR - a) % P.RING_YEARS] = 0.0
        ring.pool_f, ring.pool_m, ring.pool_age = 12.0, 7.0, 152.5
        demographics_model._refresh_denominators(ring)
        ring.total = ring.people()
        before = (list(ring.f), list(ring.m))
        pop = ring.total * 1.004
        inp = self.INP
        fixtures = {}
        if flows is not None:
            stub_flows = False
            inp = dataclasses.replace(
                self.INP, techs=self.INP.techs | flows.get("techs", frozenset()), crisis=flows["crisis"],
                inflow_years=flows.get("inflow_years") or 0, female_job_share=flows["fjob_share"])
            war_dead, kills = flows.get("war") or 0.0, flows.get("kills") or 0.0
            # the residual the script reads, and what the model is told: a residual inside the noise band is none
            pop = ring.total + flows["eb"] - flows["ed"] - war_dead - kills + flows["migration"]
            migration = 0.0 if abs(flows["migration"]) < P.RESIDUAL_NOISE_SHARE * ring.total else flows["migration"]
            fixtures = {"te_demog_crisis": flows["crisis"],
                        "te_demog_family_transport": sum(v for tech, v in P.FAMILY_TRANSPORT_TECHS.items()
                                                         if tech in inp.techs)}
        stub = None
        if stub_flows:
            prof = demographics_model.migrant_profile(inp)
            locals_ = {
                "te_dg_war_ff": min(0.5, war_dead * (1 - P.WAR_DEAD_MALE_SHARE) / ring.women_18_40),
                "te_dg_war_fm": min(0.5, war_dead * P.WAR_DEAD_MALE_SHARE / ring.men_18_40),
                "te_dg_kill": min(0.9, kills / ring.total),
                "te_dg_mig_in": max(migration, 0.0),
                "te_dg_mig_out": max(-migration, 0.0),
            }
            for c in range(len(P.MIGRANT_CLASSES)):
                locals_[f"te_dg_pf{c}"], locals_[f"te_dg_pm{c}"] = prof[(c, "f")], prof[(c, "m")]
            stub = {"te_demog_flows": "\n".join(f"set_local_variable = {{ name = {k} value = {v!r} }}"
                                                for k, v in locals_.items())}
        eng = _engine_for(inp, self.YEAR + 1, pop, effects=stub)
        eng.fixtures.update(fixtures)
        for k in range(P.RING_YEARS):
            if before[0][k] or before[1][k]:
                eng.vars[f"te_dg_f{k}"], eng.vars[f"te_dg_m{k}"] = before[0][k], before[1][k]
        eng.vars.update(te_dg_pf=ring.pool_f, te_dg_pm=ring.pool_m, te_dg_pa=ring.pool_age, te_dg_scale=scale,
                        te_dg_year=self.YEAR, te_dg_people=ring.total, te_dg_raw=ring.total / scale,
                        te_dg_f1840=ring.women_18_40, te_dg_m1840=ring.men_18_40)
        for c in range(len(P.MIGRANT_CLASSES)):
            eng.vars[f"te_dg_cf{c}"], eng.vars[f"te_dg_cm{c}"] = ring.class_f[c], ring.class_m[c]
        if flows is not None:
            eng.vars.update(te_dg_pop_last=ring.total, te_dg_eb=flows["eb"], te_dg_ed=flows["ed"],
                            te_dg_fjob_share=flows["fjob_share"])
            for name, key in (("te_dg_war_in", "war"), ("te_dg_kills_in", "kills"),
                              ("te_dg_inflow_years", "inflow_years")):
                if flows.get(key) is not None:
                    eng.vars[name] = float(flows[key])
        eng.call("te_demog_step")
        figures = demographics_model.step(ring, inp, self.YEAR + 1, engine_pop=pop, war_dead=war_dead,
                                          kills=kills, migration=migration)
        return eng, ring, figures, pop

    def check_step(self, eng, ring, figures, pop):
        self.close(eng.vars["te_dg_births"], figures["births"], what="births")
        self.close(eng.vars["te_dg_deaths"], figures["deaths"], what="deaths")
        # the script drops a cohort under half a person; the model keeps it
        kept = demographics_model.Ring(year=ring.year, scale=1.0)
        for k in range(P.RING_YEARS):
            a = ring.age_of_slot(k)
            if f"te_dg_f{k}" not in eng.vars:
                self.assertTrue(ring.f[k] < 0.5 and ring.m[k] < 0.5, f"age {a} dropped with people in it")
                continue
            self.close(eng.vars[f"te_dg_f{k}"], ring.f[k], what=f"women aged {a}")
            self.close(eng.vars[f"te_dg_m{k}"], ring.m[k], what=f"men aged {a}")
            kept.f[k], kept.m[k] = ring.f[k], ring.m[k]
        self.close(eng.vars["te_dg_pf"], ring.pool_f, what="pool women")
        self.close(eng.vars["te_dg_pm"], ring.pool_m, what="pool men")
        self.close(eng.vars["te_dg_pa"], ring.pool_age, what="pool's mean age")
        kept.pool_f, kept.pool_m = ring.pool_f, ring.pool_m
        raw = sum(kept.f) + sum(kept.m) + kept.pool_f + kept.pool_m
        self.close(eng.vars["te_dg_raw"], raw, what="raw ring")
        kept.scale = pop / raw
        self.close(eng.vars["te_dg_scale"], kept.scale, what="scale")
        self.close(eng.vars["te_dg_people"], pop, what="people")
        self.assertEqual(eng.vars["te_dg_year"], self.YEAR + 1)
        demographics_model._refresh_denominators(kept)
        for c in range(len(P.MIGRANT_CLASSES)):
            self.close(eng.vars[f"te_dg_cf{c}"], kept.class_f[c], what=f"class {c} women")
            self.close(eng.vars[f"te_dg_cm{c}"], kept.class_m[c], what=f"class {c} men")
        self.close(eng.vars["te_dg_f1840"], kept.women_18_40, what="women 18-40")
        self.close(eng.vars["te_dg_m1840"], kept.men_18_40, what="men 18-40")
        rows = kept.by_age()
        for b, ages in enumerate(BANDS):
            self.close(eng.vars[f"te_dg_bf{b}"], sum(f for a, f, _m in rows if a in ages), what=f"band {b} women")
            self.close(eng.vars[f"te_dg_bm{b}"], sum(m for a, _f, m in rows if a in ages), what=f"band {b} men")

    def test_step_without_flows(self):
        """The script's own te_demog_flows with nothing to flow: no pending dead, a residual of 0."""
        eng, *rest = self.step_both(flows=dict(eb=0.0, ed=0.0, crisis=0.0, fjob_share=0.3, migration=0.0))
        self.check_step(eng, *rest)
        self.assertEqual(eng.vars["te_dg_net_migration"], 0.0)
        self.assertEqual(eng.vars["te_dg_inflow_years"], 0.0)

    def test_step_with_war_kills_and_immigration(self):
        self.check_step(*self.step_both(war_dead=900.0, kills=1500.0, migration=4000.0))

    def test_step_with_war_kills_and_emigration(self):
        self.check_step(*self.step_both(war_dead=300.0, kills=200.0, migration=-6000.0))

    def test_step_with_an_empty_open_slot_and_old_ages(self):
        """Nobody aged 90 and over: empty slots are skipped while the trackers advance, and the
        pool ages and scales with nobody folding into it."""
        eng, ring, figures, pop = self.step_both(war_dead=500.0, kills=800.0, migration=2000.0, empty_from=90)
        self.check_step(eng, ring, figures, pop)
        for a in range(91, P.RING_YEARS):
            self.assertNotIn(f"te_dg_f{(self.YEAR + 1 - a) % P.RING_YEARS}", eng.vars, f"age {a}")
        self.assertIn(f"te_dg_f{(self.YEAR + 1) % P.RING_YEARS}", eng.vars, "the open slot takes the births")

    def test_step_with_emigration_at_the_cap(self):
        """Departures over half a cohort's survivors stop at half (demographics_model.step)."""
        eng, ring, figures, pop = self.step_both(migration=-0.45 * self.POP)
        self.check_step(eng, ring, figures, pop)

    # -- the script's own flows (te_demog_flows) ------------------------------------------------

    def check_flows(self, eng, flows, want_inflow_years):
        """The flow locals te_demog_flows set equal the model's war shares, kill share, migrant
        split and profile, and it consumed what was pending."""
        inp = dataclasses.replace(
            self.INP, techs=self.INP.techs | flows.get("techs", frozenset()), crisis=flows["crisis"],
            inflow_years=flows.get("inflow_years") or 0, female_job_share=flows["fjob_share"])
        prof = demographics_model.migrant_profile(inp)
        for c in range(len(P.MIGRANT_CLASSES)):
            self.close(eng.locals[f"te_dg_pf{c}"], prof[(c, "f")], rel=1e-9, what=f"profile, class {c} women")
            self.close(eng.locals[f"te_dg_pm{c}"], prof[(c, "m")], rel=1e-9, what=f"profile, class {c} men")
        self.close(sum(eng.locals[f"te_dg_p{s}{c}"] for s in "fm" for c in range(len(P.MIGRANT_CLASSES))), 1.0,
                   what="the profile sums to 1")
        for name in ("te_dg_war_in", "te_dg_kills_in"):
            self.assertNotIn(name, eng.vars, f"{name} is taken once")
        self.assertEqual(eng.vars["te_dg_inflow_years"], want_inflow_years)

    def test_flows_for_immigration_with_war_dead_and_kills(self):
        flows = dict(eb=2500.0, ed=2100.0, migration=4000.0, crisis=0.2, fjob_share=0.4, war=900.0, kills=1500.0,
                     inflow_years=12, techs=frozenset({"railways", "paddle_steamer"}))   # past chain migration's cap
        eng, ring, figures, pop = self.step_both(flows=flows)
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=13)
        self.close(eng.vars["te_dg_net_migration"], 4000.0, what="net migration")
        self.assertGreater(eng.locals["te_dg_mig_in"], 0)
        self.assertEqual(eng.locals["te_dg_mig_out"], 0)

    def test_flows_for_emigration(self):
        flows = dict(eb=2500.0, ed=2100.0, migration=-6000.0, crisis=0.35, fjob_share=0.1, war=300.0, inflow_years=5)
        eng, ring, figures, pop = self.step_both(flows=flows)
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=0)
        self.close(eng.vars["te_dg_net_migration"], -6000.0, what="net migration")
        self.assertEqual(eng.locals["te_dg_mig_in"], 0)
        self.assertGreater(eng.locals["te_dg_mig_out"], 0)

    def test_flows_ignore_a_residual_inside_the_noise_band(self):
        """0.2% of the people is model error: no migrants, and the inflow streak ends."""
        flows = dict(eb=2500.0, ed=2100.0, migration=0.002 * self.POP, crisis=0.0, fjob_share=0.3, inflow_years=4)
        eng, ring, figures, pop = self.step_both(flows=flows)
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=0)
        self.assertEqual(eng.vars["te_dg_net_migration"], 0.0)
        flows["migration"] = 0.004 * self.POP
        eng, ring, figures, pop = self.step_both(flows=flows)
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=5)
        self.assertGreater(eng.vars["te_dg_net_migration"], 0)

    def test_flows_with_a_first_year_state_and_a_full_crisis(self):
        """No pending dead or kills, no streak variable yet; refugees take the whole profile."""
        flows = dict(eb=2500.0, ed=2100.0, migration=3000.0, crisis=1.0, fjob_share=0.3)
        eng, ring, figures, pop = self.step_both(flows=flows)
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=1)
        self.close(eng.locals["te_dg_labour"], 0.0, what="labour migrants")
        self.close(eng.locals["te_dg_family"], 0.0, what="families")

    def test_flows_hit_the_caps(self):
        """The war share stops at half a cohort, the kill share at 0.9."""
        war, kills = 5.0 * self.POP, 0.95 * self.POP
        flows = dict(eb=0.0, ed=0.0, migration=war + kills, crisis=0.0, fjob_share=0.3, war=war, kills=kills)
        eng, *_rest = self.step_both(flows=flows)
        self.assertEqual(eng.locals["te_dg_war_fm"], 0.5)
        self.assertEqual(eng.locals["te_dg_war_ff"], 0.5)
        self.assertEqual(eng.locals["te_dg_kill"], 0.9)

    def test_a_seed_drops_the_flows_pending_before_it(self):
        eng = _engine_for(self.INP, self.YEAR, self.POP)
        eng.vars.update(te_dg_war_in=500.0, te_dg_kills_in=80.0)
        eng.call("te_demog_seed")
        self.assertNotIn("te_dg_war_in", eng.vars)
        self.assertNotIn("te_dg_kills_in", eng.vars)

    # -- the orchestrator -----------------------------------------------------------------------

    def test_orchestrator_dispatch(self):
        stubs = {"te_demog_walks": "", "te_inh_refresh_rural_effects": "",
                 "te_demog_seed": "set_variable = { name = did value = 1 }",
                 "te_demog_step": "set_variable = { name = did value = 2 }"}
        cases = [   # (census year, raw, people, rule on) -> seed 1, step 2, nothing None
            ((None, None, 1000.0, True), 1),
            ((1836, 900.0, 1000.0, True), 2),
            ((1837, 900.0, 1000.0, True), None),
            ((1834, 900.0, 1000.0, True), 1),
            ((1836, 0.5, 1000.0, True), 1),
            ((1836, 0.5, 0.0, True), 2),
            ((None, None, 1000.0, False), None),
        ]
        for (census, raw, pop, rule), want in cases:
            eng = _Engine({"year": 1837.0, "state_population": pop}, triggers={"te_demog_cohorts_run": rule},
                          effects=stubs)
            if census is not None:
                eng.vars.update(te_dg_year=float(census), te_dg_raw=raw)
            eng.call("te_demog_state_yearly")
            self.assertEqual(eng.vars.get("did"), want, (census, raw, pop, rule))


class _CountryEngine(_Engine):
    """_Engine plus the two iterators the country effects use. every_scope_war runs its body once
    per war in `wars` (the owner's dead in it, read through te_demog_war_dead_root); every_scope_state
    once per state in `states` (a dict of that state's variables, the locals staying shared)."""

    def __init__(self, wars=(), states=(), **kwargs):
        super().__init__(**kwargs)
        self.wars, self.states = list(wars), list(states)

    def run(self, items):
        batch = []
        for item in items:
            if item[0] in ("every_scope_war", "every_scope_state"):
                super().run(batch)
                batch = []
                self._iterate(item[0], item[2])
            else:
                batch.append(item)
        super().run(batch)

    def _iterate(self, key, arg):
        body = [i for i in arg if i[0] != "limit"]
        if key == "every_scope_war":
            for dead in self.wars:
                self.fixtures["te_demog_war_dead_root"] = float(dead)
                self.run(body)
            return
        country_vars = self.vars
        for state_vars in self.states:
            self.vars = state_vars
            if self.holds(_find(arg, "limit")):
                self.run(body)
        self.vars = country_vars


class TestFlows(unittest.TestCase):
    def test_finished_war_never_returns_its_dead(self):
        """Review Focus 4: the monthly change in summed war dead is floored at zero."""
        body = _block(_text(EFFECTS), "te_demog_country_monthly")
        self.assertRegex(body, r"subtract = var:te_dg_war_seen\s+min = 0")

    def test_kill_sites_record_their_dead(self):
        effects = _text(ROOT / "common" / "scripted_effects" / "extra_effects.txt")
        for name in ("nuclear_industrial_strike", "nuclear_tactical_strike"):
            self.assertIn("te_demog_note_kills", _block(effects, name), name)
        on_actions = _text(ROOT / "common" / "on_actions" / "extra_on_actions.txt")
        self.assertEqual(on_actions.count("te_demog_note_kills"), 2)   # both Violent Hostility kills

    def test_crisis_reads_devastation_as_a_percentage(self):
        """State devastation runs 0-100 (add_devastation = 10 ... capped at 100), turmoil 0-1."""
        body = _block(_text(VALUES), "te_demog_crisis")
        self.assertIn("add = { value = devastation divide = 100 }", body)
        self.assertNotRegex(body, r"add = devastation\b")
        self.assertIn("add = turmoil", body)

    def test_tactical_strike_tallies_its_soldiers_in_a_local(self):
        """Inside the pop walk change_variable writes the pop's own variable and total_population is a
        country trigger: the tally has to be a local, in total_size, added to the state's after the walk."""
        effects = _text(ROOT / "common" / "scripted_effects" / "extra_effects.txt")
        body = _block(effects, "nuclear_tactical_strike")
        start = body.index("every_scope_pop = {")
        depth, i = 1, body.index("{", start) + 1
        while depth:
            depth += {"{": 1, "}": -1}.get(body[i], 0)
            i += 1
        walk = body[start:i]
        self.assertIn("change_local_variable", walk)
        self.assertIn("total_size", walk)
        self.assertNotIn("change_variable", walk)
        self.assertNotIn("total_population", walk)
        after = body[i:]
        self.assertLess(body.index("set_local_variable = { name = te_dg_ts value = 0 }"), start)
        self.assertLess(after.index("add = local_var:te_dg_ts"), after.index("te_demog_note_kills"))
        self.assertLess(after.index("te_demog_note_kills"), after.index("kill_population_percent_in_state"))

    def test_residual_ignores_noise(self):
        body = _block(_text(EFFECTS), "te_demog_flows")
        self.assertIn("te_demog_k_residual_noise_share", body)

    def test_country_pulses_are_hooked(self):
        text = _text(DEMOG_ON_ACTIONS)
        self.assertRegex(_block(text, "on_monthly_pulse_country"), r"te_demog_country_monthly_on_action")
        self.assertRegex(_block(text, "on_yearly_pulse_country"), r"te_demog_country_yearly_on_action")
        monthly = _block(text, "te_demog_country_monthly_on_action")
        self.assertIn("te_demog_country_monthly = yes", monthly)
        self.assertNotIn("te_demog_cohorts_run", monthly)   # Task 11's war shock reads the same total
        self.assertIn("te_demog_country_yearly = yes", _block(text, "te_demog_country_yearly_on_action"))
        self.assertIn("te_demog_cohorts_run = yes", _block(_text(EFFECTS), "te_demog_country_yearly"))

    def test_flows_set_every_local_the_step_reads(self):
        """Whatever the branch, te_demog_flows leaves the locals te_demog_no_flows names: each is set
        at its top level (one tab), not inside an if."""
        flows = _block(_text(EFFECTS), "te_demog_flows")
        body = flows + _block(_text(GENERATED_EFFECTS), "te_demog_set_profile")
        self.assertRegex(flows, r"(?m)^\tte_demog_set_profile = yes$", "the profile is set unconditionally")
        names = re.findall(r"name = (te_dg_\w+) value", _block(_text(EFFECTS), "te_demog_no_flows"))
        self.assertEqual(len(names), 15)
        for name in names:
            self.assertIsNotNone(re.search(rf"^\tset_local_variable = \{{\s+name = {name}\s+value", body, re.M), name)

    def test_each_war_adds_its_dead_to_the_year(self):
        eng = _CountryEngine(wars=[100, 50], fixtures={})
        for wars, want_seen, want_year in (
            ([100, 50], 150, 0),   # first run: starts from the dead already counted
            ([130, 80], 210, 60),
            ([130], 130, 60),      # a war ended: the sum fell, nothing is returned or subtracted
            ([140], 140, 70),
            ([], 0, 70),           # peace
        ):
            eng.wars = wars
            eng.call("te_demog_country_monthly")
            self.assertEqual((eng.vars["te_dg_war_seen"], eng.vars["te_dg_war_year"]), (want_seen, want_year), wars)

    def _states(self, *soldiers_people_census):
        out = []
        for soldiers, people, census in soldiers_people_census:
            state = {"te_dg_soldiers": float(soldiers), "te_dg_people": float(people)}
            if census:
                state["te_dg_year"] = 1836.0
            out.append(state)
        return out

    def test_the_years_dead_go_to_states_by_their_soldiers(self):
        states = self._states((300, 10000, True), (100, 30000, True), (600, 5000, False))
        states[0]["te_dg_war_in"] = 5.0   # an earlier share not yet taken is kept
        eng = _CountryEngine(states=states, fixtures={}, triggers={"te_demog_cohorts_run": True})
        eng.vars.update(te_dg_war_year=1000.0)
        eng.call("te_demog_country_yearly")
        self.assertEqual(states[0]["te_dg_war_in"], 5.0 + 750.0)
        self.assertEqual(states[1]["te_dg_war_in"], 250.0)
        self.assertNotIn("te_dg_war_in", states[2], "a state with no census is skipped")
        self.assertEqual(eng.vars["te_dg_war_year"], 0.0)

    def test_a_country_without_soldiers_shares_by_people(self):
        states = self._states((0, 10000, True), (0, 30000, True))
        eng = _CountryEngine(states=states, fixtures={}, triggers={"te_demog_cohorts_run": True})
        eng.vars.update(te_dg_war_year=400.0)
        eng.call("te_demog_share_war_dead")
        self.assertEqual((states[0]["te_dg_war_in"], states[1]["te_dg_war_in"]), (100.0, 300.0))

    def test_no_dead_or_no_rule_shares_nothing(self):
        for rule, year in ((True, 0.0), (False, 500.0)):
            states = self._states((300, 10000, True))
            eng = _CountryEngine(states=states, fixtures={}, triggers={"te_demog_cohorts_run": rule})
            eng.vars.update(te_dg_war_year=year)
            eng.call("te_demog_country_yearly")
            self.assertNotIn("te_dg_war_in", states[0], (rule, year))
            self.assertEqual(eng.vars["te_dg_war_year"], year)

    def test_known_kills_add_up_and_only_where_the_census_runs(self):
        call = "te_demog_note_kills = { VALUE = var:struck }"
        for rule, census, want in ((True, True, 700.0), (True, False, None), (False, True, None)):
            eng = _Engine({}, triggers={"te_demog_cohorts_run": rule})
            eng.vars["struck"] = 300.0
            if census:
                eng.vars["te_dg_year"] = 1836.0
            eng.run(_parse_script(call))
            eng.vars["struck"] = 400.0
            eng.run(_parse_script(call))
            self.assertEqual(eng.vars.get("te_dg_kills_in"), want, (rule, census))
