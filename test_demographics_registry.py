"""Demographics phase 1 wiring (docs/superpowers/plans/2026-10-08-demographics-phases-0-1.md).

Static checks on the script: the rule's settings and wrappers, guarded divisions, the
pulse wiring, the gates around every cohort entry point. Later tasks add tests here.
"""

import dataclasses
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
DISPLAY_VALUES = ROOT / "common" / "script_values" / "te_demog_display_values.txt"
INH_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_inheritance_on_actions.txt"
DEMOG_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_demog_on_actions.txt"
WEALTH_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_wealth_effects.txt"
GENERATED_VALUES = ROOT / "common" / "script_values" / "te_demog_generated_values.txt"
GENERATED_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_generated_effects.txt"
VALUES = ROOT / "common" / "script_values" / "te_demog_values.txt"
FAST_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_fast_effects.txt"
RATE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_rate_effects.txt"
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

    def test_the_walk_expects_each_pops_own_rates(self):
        """Each pop's curves x its own multiplier, floored per pop; no state-level 1 + modifier:state_*_mult,
        which missed literacy, starvation and every class, workplace and working-conditions term
        (docs/testing/demographics-growth-probe-results-2026-10-09.md)."""
        body = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_walks"))
        self.assertIn("set_local_variable = { name = te_dg_p_eb value = te_demog_pop_engine_births }", body)
        self.assertIn("set_local_variable = { name = te_dg_p_ed value = te_demog_pop_engine_deaths }", body)
        self.assertIn("add = { value = local_var:te_dg_p_eb multiply = te_demog_pop_birth_mult }", body)
        self.assertIn("add = { value = local_var:te_dg_p_ed multiply = te_demog_pop_death_mult }", body)
        self.assertNotIn("modifier:state_birth_rate_mult", body)
        self.assertNotIn("modifier:state_mortality_mult", body)

    def test_the_walk_expects_the_steps_months(self):
        """A month's curves x the months the step covers: 12 on the yearly pulse, the clock's window under
        fast mode (te_demog_step_months), never a literal 12."""
        body = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_walks"))
        for var in ("te_dg_eb", "te_dg_ed"):
            block = re.search(r"name = %s\s+value = \{([^{}]*)\}" % var, body)
            self.assertIsNotNone(block, var)
            self.assertIn("multiply = te_demog_step_months", block.group(1))
            self.assertNotIn("multiply = 12", block.group(1))

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

    def test_ownership_fractions_are_read_only_from_built_buildings(self):
        """Observer test of #830: a building whose first level is under construction
        logs "ownership_fraction requires the building to be built" three times a pulse."""
        body = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_walks"))
        limit = re.search(r"limit = \{([^{}]*)\}\s*change_local_variable = \{ name = te_dg_w_priv", body)
        self.assertIsNotNone(limit)
        self.assertIn("level > 0", limit.group(1))
        self.assertIn("te_demog_is_capital_building = yes", limit.group(1))

    def test_the_state_subtab_gate_needs_no_player(self):
        """Observer test of #830: an observer has no player, so a GetPlayer root logged an
        error every frame the state panel was open. The gate reads only the rule."""
        panel = _text(ROOT / "gui" / "states_panel.gui")
        reads = re.findall(r"GetScriptedGui\('te_pops_demog_tab_sgui'\)\.IsShown\( GuiScope\.SetRoot\( ([\w.]+) \)", panel)
        self.assertEqual(reads, ["State.GetOwner.MakeScope"] * 2)
        content = _text(ROOT / "gui" / "te_demographics_widgets.gui")
        content = content[content.index("type te_state_demog_overview"):]
        self.assertNotIn("GetPlayer", content, "the state's sections read only the state")


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


class TestStateGini(unittest.TestCase):
    """te_demog_state_gini (the state's wealth bands into the generated formula) against the model."""

    def shown(self, bands):
        eng = _Engine({})
        for k in range(1, P.GINI_BANDS + 1):
            n, y = bands.get(k, (0.0, 0.0))
            eng.vars[f"te_dg_gn{k}"], eng.vars[f"te_dg_gy{k}"] = float(n), float(y)
        eng.call("te_demog_state_gini")
        return eng.vars["te_dg_gini"]

    def test_matches_the_model_on_random_states(self):
        rng = random.Random(7)
        for _ in range(200):
            bands, per_head = {}, 0.0
            for k in range(1, P.GINI_BANDS + 1):
                per_head += rng.uniform(0.0, 40.0)
                n = rng.choice([0, rng.randint(1, 50000)])
                bands[k] = (n, n * per_head)
            expected = demographics_model.shown_gini(demographics_model.grouped_gini(list(bands.values())))
            self.assertAlmostEqual(self.shown(bands), expected, places=9, msg=str(bands))

    def test_no_people_or_no_income_shows_the_floor(self):
        self.assertAlmostEqual(self.shown({}), 1 - P.GINI_SHOWN_EQUALITY, places=9)
        self.assertAlmostEqual(self.shown({1: (10, 0), 4: (5, 0)}), 1 - P.GINI_SHOWN_EQUALITY, places=9)

    def test_state_and_country_share_one_generated_formula(self):
        text = _text(WEALTH_EFFECTS)
        for caller in ("te_demog_state_gini", "te_demog_wc_national"):
            self.assertIn("te_demog_gini_from_locals = yes", _block(text, caller), caller)
        self.assertNotIn("te_demog_gini_from_locals = {", text, "the formula is generated, not hand-written")
        self.assertIn("name = te_dg_gini", _block(_text(GENERATED_EFFECTS), "te_demog_gini_from_locals"))

    def test_the_walk_sums_wealth_bands_not_strata(self):
        walk = _block(_text(EFFECTS), "te_demog_walks")
        for call in ("te_demog_gini_band_init = yes", "te_demog_gini_band_add = yes", "te_demog_gini_band_store = yes"):
            self.assertIn(call, walk)
        self.assertNotIn("strata = upper", walk)
        start = walk.index("every_scope_pop = {") + len("every_scope_pop = {")
        depth, i = 1, start
        while depth:
            depth += {"{": 1, "}": -1}.get(walk[i], 0)
            i += 1
        pops = walk[start:i - 1]
        self.assertIn("te_demog_gini_band_add = yes", pops, "each pop adds itself, inside the pop loop")
        self.assertNotIn("te_demog_gini_band_store = yes", pops)


class TestStep(unittest.TestCase):
    def test_orchestrator_branches(self):
        """Seed when there is no census, a gap of more than a year, an emptied ring or people more
        than 25% off the last census's; step once a year; nothing on a second pulse in the same
        year (Review Focus 3)."""
        self.assertIn("te_demog_state_census = yes", _block(_text(EFFECTS), "te_demog_state_yearly"))
        body = _block(_text(EFFECTS), "te_demog_state_census")
        self.assertIn("te_demog_cohorts_run = yes", body)
        self.assertIn("te_demog_seed = yes", body)
        self.assertIn("te_demog_step = yes", body)
        self.assertIn("local_var:te_dg_gap > 1", body)
        self.assertIn("local_var:te_dg_gap = 1", body)
        self.assertIn("value = { value = state_population subtract = { value = var:te_dg_pop_last multiply = 1.25 } }", body)
        self.assertIn("value = { value = state_population subtract = { value = var:te_dg_pop_last multiply = 0.75 } }", body)

    def test_the_branch_limits_compare_locals(self):
        """Observer tests of #830 and #833 (2026-10-09): state_population > { value =
        var:te_dg_pop_last multiply = 1.25 } held for every state with people, even 0.3% up, and its
        0.75 twin for none, so every state seeded at every pulse and none stepped. The pulse takes
        the move into locals, as people less 1.25 and 0.75 times the last census's, and its limits
        compare those with 0."""
        body = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_state_census"))
        self.assertNotRegex(body, r"state_population [<>]=? \{")
        self.assertIn("local_var:te_dg_over > 0", body)
        self.assertIn("local_var:te_dg_under < 0", body)
        self.assertIn("value = { value = te_demog_year subtract = var:te_dg_year }", body)
        self.assertIn("set_variable = { name = te_dg_year value = te_demog_year }", _block(_text(EFFECTS), "te_demog_set_scale"))

    def test_no_script_compares_state_population_with_a_block(self):
        """The form above misfired in game with no log line, so nothing in the mod's script uses it:
        compare state_population with a number, or take the difference into a local first."""
        hits = []
        for path in [*ROOT.glob("common/**/*.txt"), *ROOT.glob("events/**/*.txt")]:
            text = re.sub(r"#[^\n]*", "", _text(path))
            for m in re.finditer(r"\bstate_population\s*(?:[<>]=?|!=|=)\s*\{", text):
                line = text.count("\n", 0, m.start()) + 1
                hits.append(f"{path.relative_to(ROOT)}:{line}")
        self.assertEqual(hits, [])

    def test_every_cohort_entry_point_is_gated(self):
        """Review Focus 5: nothing writes a cohort without te_demog_cohorts_run."""
        text = _text(EFFECTS)
        for caller in ("te_demog_state_yearly", "te_demog_country_game_start", "te_demog_country_monthly"):
            body = _block(text, caller)
            for entry in ("te_demog_seed = yes", "te_demog_seed_off_pulse = yes", "te_demog_step = yes",
                          "te_demog_share_war_dead = yes"):
                if entry in body:
                    gate = body.rfind("te_demog_cohorts_run = yes", 0, body.index(entry))
                    self.assertNotEqual(gate, -1, f"{caller}: {entry} before the gate")

    def test_family_limitation_matches_the_params(self):
        modifiers = _text(ROOT / "common" / "static_modifiers" / "te_demog_modifiers.txt")
        body = _block(modifiers, "te_demog_family_limitation")
        self.assertIn(f"{P.MEANS_SHIFT_TYPE} = {P.FAMILY_LIMITATION_MEANS}", body)
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


FIXED_MAX = (2 ** 63 - 1) / 1e5   # the largest value script holds: an i64 in units of 1e-5


class _Engine:
    """Enough of the engine to run the census: value blocks applied in order (min and max clamp
    where they stand), variables and locals, if / else_if / else, while, triggers, and scripted
    effects with their $ARG$ substituted as text. A read of a variable or local that was never
    set fails, as does an argument the callee doesn't name (the script_argument_audit rule).
    `fixtures` stand in for engine reads and for script values that read the owner. With
    truncate=True every operation and every stored value is cut to five decimals, toward zero:
    the engine's fixed point (values are i64 x 1e-5), and a value past FIXED_MAX fails."""

    def __init__(self, fixtures, triggers=None, effects=None, truncate=False):
        self.truncate = truncate
        self.effects = _raw_blocks([EFFECTS, GENERATED_EFFECTS, WEALTH_EFFECTS, FAST_EFFECTS, RATE_EFFECTS])
        self.effects.update(effects or {})
        self.values = _raw_blocks([VALUES, GENERATED_VALUES, DISPLAY_VALUES])
        self.triggers = _raw_blocks([TRIGGERS])
        # the history store (te_history_country_is_tracked) has no containers here, and the console's
        # census log (te_demog_census_log_on) only writes debug_log lines: both off unless a test says;
        # so is fast mode's census clock (te_demog_clock_on), whose globals a test gives as fixtures
        # ("global_var:te_demog_clock" and the like), and the rule's Full (te_demog_effects_run): off unless a
        # test says (the real trigger reads has_game_rule, which _Engine doesn't know)
        self.trigger_fixtures = {"te_history_country_is_tracked": False, "te_demog_census_log_on": False,
                                 "te_demog_clock_on": False, "te_demog_effects_run": False, **(triggers or {})}
        self.fixtures = dict(fixtures)
        self.vars, self.locals, self._trees = {}, {}, {}
        self.modifiers = {}   # add_modifier's name -> its multiplier

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

    def _q(self, x):
        if not self.truncate:
            return x
        assert abs(x) <= FIXED_MAX, f"fixed-point overflow: {x:.4g}"
        return math.trunc(x * 1e5 + (1e-7 if x >= 0 else -1e-7)) / 1e5

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
            acc = self._q(acc)
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
        if key == "has_modifier":
            return arg in self.modifiers
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
                store[_find(arg, "name")] = self._q(self.value(_find(arg, "value")))
            elif key in ("change_local_variable", "change_variable"):
                store = self.locals if key == "change_local_variable" else self.vars
                name = _find(arg, "name")
                assert name in store, f"change of unset {name}"
                store[name] = self._ops([i for i in arg if i[0] != "name"], store[name])
            elif key == "clamp_variable":
                name = _find(arg, "name")
                assert name in self.vars, f"clamp of unset {name}"
                lo, hi = self.value(_find(arg, "min")), self.value(_find(arg, "max"))
                self.vars[name] = min(max(self.vars[name], lo), hi)
            elif key == "remove_variable":
                self.vars.pop(arg, None)
            elif key == "add_modifier":
                self.modifiers[_find(arg, "name")] = self._q(self.value(_find(arg, "multiplier")))
            elif key == "remove_modifier":
                assert arg in self.modifiers, f"remove of absent modifier {arg}"
                del self.modifiers[arg]
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


def _engine_for(inp, year, pop, effects=None, engine=None):
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
    eng = (engine or _Engine)(fixtures, triggers={"te_demog_cohorts_run": True}, effects=effects)
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

    def test_the_pyramid_scale_is_stored_with_the_figures(self):
        """Review on #830: the bars read te_dg_pyr_max, written once at the census, instead of a
        script value that reads all 36 bands in every bar's range each frame."""
        eng = _engine_for(self.INP, 1836, self.POP)
        eng.call("te_demog_seed")
        bands = [eng.vars[f"te_dg_b{s}{b}"] for s in "fm" for b in range(18)]
        self.assertAlmostEqual(eng.vars["te_dg_pyr_max"], max(bands))
        gui = _text(ROOT / "gui" / "te_demographics_widgets.gui")
        self.assertNotIn("ScriptValue('te_demog_pyramid_max')", gui)
        self.assertNotIn("ScriptValue('te_demog_state_pyramid_max')", gui)
        self.assertEqual(gui.count("Var('te_dg_pyr_max').GetValue"), 40)
        census = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertGreater(census.index("set_variable = { name = te_dg_pyr_max value = te_demog_pyramid_max }"),
                           census.index("te_demog_project = yes"), "after the outline, which shares the scale")

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
        self.assertFalse("te_dg_prev_median" in eng.vars, "a first census has no previous figures")
        eng.vars["te_dg_median"] = 99.0
        eng.call("te_demog_state_figures")
        self.assertFalse("te_dg_prev_median" in eng.vars, "a seed's figures are no year to compare with")
        eng.vars["te_dg_stepped"] = 1.0   # as after a step
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
                  flows=None, entry="te_demog_step", engine=None, on_top=None, full=False):
        """One step from the same state on both sides: the model's seed at a scale off 1, with
        people in the two oldest cohorts and in the pool. The flows reach the script one of two ways:
        stub_flows feeds war_dead, kills and migration through a te_demog_flows built from the
        model's own formulas (it tests the step alone); flows= runs the script's own te_demog_flows
        from the state's variables, against the same flows given to the model. flows is a dict:
          eb, ed (the engine's births and deaths), migration (the residual before the noise rule),
          crisis, fjob_share, techs (added to INP's), and the optional pending war (te_dg_war_in),
          kills (te_dg_kills_in) and inflow_years, left out = the variable doesn't exist.
        empty_from: nobody from that age up (the slots hold no variable; the pool keeps its people),
        the ring of the game's first decades, when the open slot is empty at the fold.
        on_top = (births, deaths): the share by which the engine's expected events over the window ran
        above the model's rates M aimed at (phase 2 step 4); full = the rule's Full setting, under which
        alone the step takes those as its on-top scales."""
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
        eng = _engine_for(inp, self.YEAR + 1, pop, effects=stub, engine=engine)
        eng.fixtures.update(fixtures)
        bz = dz = 0.0
        if full:
            eng.trigger_fixtures["te_demog_effects_run"] = True
        if on_top is not None:
            assert flows is None, "the on-top scales and the script's own flows both write te_dg_eb"
            # the model's rates M aimed at, and the engine's expected events over the window at today's people
            want_b, want_d = 40.0 * pop / 1000, 30.0 * pop / 1000
            eng.vars.update(te_dg_cbr_model=40.0, te_dg_cdr_model=30.0,
                            te_dg_eb=want_b * (1 + on_top[0]), te_dg_ed=want_d * (1 + on_top[1]))
            if full:
                bz = demographics_model.on_top_scale(want_b * (1 + on_top[0]), want_b)
                dz = demographics_model.on_top_scale(want_d * (1 + on_top[1]), want_d)
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
        eng.call(entry)
        figures = demographics_model.step(ring, inp, self.YEAR + 1, engine_pop=pop, war_dead=war_dead,
                                          kills=kills, migration=migration, births_scale=bz, deaths_scale=dz)
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

    def test_console_replay_is_the_step_with_its_lines_between(self):
        """te_debug_demog.1 option a (te_debug_demog_replay) runs the step's two halves apart and logs
        between them. It must leave the state as te_demog_step does; log the head with the flows the
        sweep then used, and the ring before the sweep rewrote te_dg_people and te_dg_scale; and remove
        its te_dg_dbg_ copies. A wrong local name in its copies reads an unset local and fails here."""
        for migration, sign in ((-6000.0, " mig=-["), (5000.0, " mig=[")):
            with self.subTest(migration=migration):
                flows = dict(eb=1200.0, ed=900.0, crisis=0.05, fjob_share=0.3, migration=migration, war=400.0,
                             kills=30.0)
                ref, _ring, _figures, pop = self.step_both(flows=flows)
                eng, *_ = self.step_both(flows=flows, entry="te_debug_demog_replay", engine=_ConsoleEngine)
                self.assertEqual(set(eng.vars), set(ref.vars), "the console's copies are all removed")
                for name, want in ref.vars.items():
                    self.close(eng.vars[name], want, what=name)
                self.assertEqual([line[:20] for line, _ in eng.logs],
                                 ["TE_DEMOG_REPLAY head", "RING_BEFORE", "RING_AFTER"])
                head, at_head = eng.logs[0]
                self.assertIn(sign, head)
                self.close(at_head["te_dg_dbg_war"], 400.0, what="war dead")
                self.close(at_head["te_dg_dbg_kills"], 30.0, what="kills")
                self.close(at_head["te_dg_dbg_mig"], migration, what="migration")
                for mine, theirs in (("tfr", "te_dg_tfr"), ("mmr", "te_dg_m_mat"), ("m_inf", "te_dg_m_inf"),
                                     ("m_ext", "te_dg_m_ext"), ("m_chr", "te_dg_m_chr")):
                    self.close(at_head[f"te_dg_dbg_{mine}"], ref.vars[theirs], what=mine)
                self.close(sum(at_head[f"te_dg_dbg_p{s}{c}"] for s in "fm" for c in range(len(P.MIGRANT_CLASSES))),
                           1.0, rel=1e-6, what="profile")
                before, after = eng.logs[1][1], eng.logs[2][1]
                self.assertEqual(before["te_dg_scale"], 1.03, "the before ring is logged before the sweep")
                self.close(after["te_dg_people"], pop, what="people after")
                self.close(after["te_dg_scale"], ref.vars["te_dg_scale"], what="scale after")

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
        self.close(eng.vars["te_dg_mig_raw"], -6000.0, what="the residual before the noise band")
        self.assertEqual(eng.locals["te_dg_mig_in"], 0)
        self.assertGreater(eng.locals["te_dg_mig_out"], 0)

    def test_flows_ignore_a_residual_inside_the_noise_band(self):
        """0.2% of the people is model error: no migrants, and the inflow streak ends."""
        flows = dict(eb=2500.0, ed=2100.0, migration=0.002 * self.POP, crisis=0.0, fjob_share=0.3, inflow_years=4)
        eng, ring, figures, pop = self.step_both(flows=flows)
        self.check_step(eng, ring, figures, pop)
        self.check_flows(eng, flows, want_inflow_years=0)
        self.assertEqual(eng.vars["te_dg_net_migration"], 0.0)
        # the census log's gate check reads the residual before the band (te_debug_demog_census_line)
        self.close(eng.vars["te_dg_mig_raw"], 0.002 * self.POP, what="the residual before the noise band")
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
        stubs = {"te_demog_walks": "", "te_inh_refresh_rural_effects": "", "te_demog_wc_state_yearly": "",
                 "te_inh_refresh_wc_state_effects": "",
                 "te_demog_seed": "set_variable = { name = did value = 1 }",
                 "te_demog_step": "set_variable = { name = did value = 2 }"}
        cases = [   # (census year, raw, people, people at the census, rule on) -> seed 1, step 2, nothing None
            ((None, None, 1000.0, None, True), 1),
            ((1836, 900.0, 1000.0, 1000.0, True), 2),
            ((1837, 900.0, 1000.0, 1000.0, True), None),
            ((1834, 900.0, 1000.0, 1000.0, True), 1),
            ((1836, 0.5, 1000.0, 1000.0, True), 1),
            ((1836, 0.5, 0.0, 0.0, True), 2),
            ((None, None, 1000.0, None, False), None),
            # a state merged or split: people more than a quarter off the last census's
            ((1836, 900.0, 1251.0, 1000.0, True), 1),
            ((1836, 900.0, 749.0, 1000.0, True), 1),
            ((1836, 900.0, 1250.0, 1000.0, True), 2),
            ((1836, 900.0, 750.0, 1000.0, True), 2),
            ((1837, 900.0, 1400.0, 1000.0, True), 1),
        ]
        for (census, raw, pop, pop_last, rule), want in cases:
            eng = _Engine({"year": 1837.0, "state_population": pop}, triggers={"te_demog_cohorts_run": rule},
                          effects=stubs)
            if census is not None:
                eng.vars.update(te_dg_year=float(census), te_dg_raw=raw, te_dg_pop_last=pop_last)
            eng.call("te_demog_state_yearly")
            self.assertEqual(eng.vars.get("did"), want, (census, raw, pop, pop_last, rule))

    # -- phase 2 step 4: the on-top scales (te_demog_on_top_scales) -----------------------------

    def test_step_with_on_top_scales_matches_the_model(self):
        eng, ring, figures, pop = self.step_both(on_top=(0.05, 0.12), full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertAlmostEqual(eng.vars["te_dg_bz"], 0.05, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_dz"], 0.12, places=5)
        self.close(eng.vars["te_dg_cbr_model"], figures["births_model"] * 1000 / pop, what="cbr_model")
        self.close(eng.vars["te_dg_cdr_model"], figures["deaths_model"] * 1000 / pop, what="cdr_model")
        self.close(eng.vars["te_dg_tfr"], figures["tfr_shown"], what="tfr shown")
        self.close(eng.vars["te_dg_tfr_model"], figures["tfr"], what="tfr model")

    def test_no_on_top_scales_outside_full(self):
        eng, ring, figures, pop = self.step_both(on_top=(0.05, 0.12), full=False)
        self.check_step(eng, ring, figures, pop)
        self.assertEqual((eng.vars["te_dg_bz"], eng.vars["te_dg_dz"]), (0.0, 0.0))

    def test_no_target_no_scales(self):
        """An old save, or the first step after phase 2 arrives: no te_dg_cbr_model yet."""
        eng, ring, figures, pop = self.step_both(full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertEqual((eng.vars["te_dg_bz"], eng.vars["te_dg_dz"]), (0.0, 0.0))

    def test_on_top_scales_are_clamped(self):
        eng, ring, figures, pop = self.step_both(on_top=(9.0, -0.99), full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertEqual(eng.vars["te_dg_bz"], P.ON_TOP_SCALE_MAX)
        self.assertEqual(eng.vars["te_dg_dz"], P.ON_TOP_SCALE_MIN)

    def test_a_seed_clears_the_target_and_the_scales(self):
        """A seed (a merge, a split, a census gap) starts the census's target over: the model's rates from before it
        are another state's or years stale, and would scale the next step's births and deaths by their ratio to
        today's. Without them that step takes no on-top scales (test_no_target_no_scales). The seed's children per
        woman is the model's own, so te_dg_tfr_model is set for the projection."""
        eng = _engine_for(self.INP, self.YEAR, self.POP)
        eng.vars.update(te_dg_cbr_model=25.0, te_dg_cdr_model=20.0, te_dg_bz=0.3, te_dg_dz=-0.2, te_dg_tfr_model=9.0)
        eng.call("te_demog_seed")
        self.assertNotIn("te_dg_cbr_model", eng.vars)
        self.assertNotIn("te_dg_cdr_model", eng.vars)
        self.assertEqual((eng.vars["te_dg_bz"], eng.vars["te_dg_dz"]), (0.0, 0.0))
        self.assertEqual(eng.vars["te_dg_tfr_model"], eng.vars["te_dg_tfr"])

    def test_step_near_the_deaths_scales_ceiling_matches_the_model(self):
        """dz at its ceiling (+4) pushes the old-age groups' rates past 100,000: the script scales the cause
        multipliers before its cap, and so does the twin (demographics_model.step)."""
        eng, ring, figures, pop = self.step_both(on_top=(0.0, 9.0), full=True)
        self.check_step(eng, ring, figures, pop)
        self.assertEqual(eng.vars["te_dg_dz"], P.ON_TOP_SCALE_MAX)
        self.close(eng.vars["te_dg_cdr_model"], figures["deaths_model"] * 1000 / pop, what="cdr_model")
        qf, qm, _mmr = demographics_model.group_rates(self.INP)
        capped = sum(q * (1 + P.ON_TOP_SCALE_MAX) >= 100000.0 for q in qf + qm)
        self.assertGreater(capped, 0, "the test must reach the cap")

    def test_the_replay_logs_the_scaled_rates(self):
        """te_debug_demog_replay logs the locals after te_demog_step_begin, so the scales are in the head's tfr
        and multipliers and the harness's replay needs no new field."""
        body = _block(_text(EFFECTS), "te_demog_step_begin")
        self.assertLess(body.index("te_demog_prepare = yes"), body.index("te_demog_on_top_scales = yes"))
        self.assertIn("te_demog_step_begin = yes", _block(_text(CONSOLE_EFFECTS), "te_debug_demog_replay"))


class TestRatesScript(unittest.TestCase):
    """te_demog_rates_refresh (te_demog_rate_effects.txt) against demographics_model.rate_term."""

    POP = 1_000_000.0

    def _eng(self, full=True, stepped=1.0, cbr=38.0, cdr=31.0, eb0=475.0 * 1_000_000, ed0=430.0 * 1_000_000,
             ebl=0.2 * 475.0 * 1_000_000, read_b=0.05, read_d=0.04):
        eng = _Engine({"state_population": self.POP, "modifier:state_birth_rate_mult": read_b,
                       "modifier:state_mortality_mult": read_d},
                      triggers={"te_demog_effects_run": full, "te_demog_cohorts_run": True})
        eng.locals.update(te_dg_w_eb0=eb0, te_dg_w_ed0=ed0, te_dg_w_ebl=ebl, te_dg_w_eb=eb0, te_dg_w_ed=ed0)
        eng.vars.update(te_dg_stepped=stepped, te_dg_cbr_model=cbr, te_dg_cdr_model=cdr)
        return eng

    def _want(self, cbr, cdr, eb0, ed0, ebl, other_b, other_d):
        mb, _ = demographics_model.rate_term(cbr * self.POP * 100 / 12, eb0,
                                             absorbed=P.LITERACY_BIRTH_PENALTY * ebl, other=other_b)
        md, _ = demographics_model.rate_term(cdr * self.POP * 100 / 12, ed0, other=other_d)
        return mb, md

    def test_script_matches_the_model(self):
        eng = self._eng()
        eng.call("te_demog_rates_refresh")
        mb, md = self._want(38.0, 31.0, 475e6, 430e6, 0.2 * 475e6, 0.05, 0.04)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
        # births down, deaths down: one modifier of each pair, multiplier |M|
        self.assertAlmostEqual(eng.modifiers["te_demog_census_births_down"], -mb, places=5)
        self.assertAlmostEqual(eng.modifiers["te_demog_census_deaths_down"], -md, places=5)
        self.assertNotIn("te_demog_census_births_up", eng.modifiers)

    def test_script_clamps_like_the_model(self):
        eng = self._eng(cbr=2.0, cdr=400.0, read_b=-0.5)
        eng.call("te_demog_rates_refresh")
        mb, md = self._want(2.0, 400.0, 475e6, 430e6, 0.2 * 475e6, -0.5, 0.04)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertEqual(eng.vars["te_dg_md"], P.RATE_TERM_MAX)
        self.assertEqual(eng.vars["te_dg_rate_clamped"], 1)

    def test_the_prior_term_comes_off_the_read(self):
        """The state read holds last step's M: the clamp's 'other' takes it off."""
        eng = self._eng(cbr=2.0, read_b=-0.5)
        eng.modifiers["te_demog_census_births_down"] = 0.3
        eng.vars["te_dg_mb"] = -0.3
        eng.call("te_demog_rates_refresh")
        mb, _ = self._want(2.0, 31.0, 475e6, 430e6, 0.2 * 475e6, -0.2, 0.04)
        self.assertAlmostEqual(eng.vars["te_dg_mb"], mb, places=5)
        self.assertAlmostEqual(eng.locals["te_dg_rate_prev_b"], -0.3)

    def test_the_refresh_leaves_its_terms_in_locals(self):
        """Fast mode runs next in the same effect, where has_modifier can't see this refresh's add or remove:
        the refresh leaves the terms in force as locals (the M it set, 0 when it clears, the prior when it skips)."""
        eng = self._eng()
        eng.call("te_demog_rates_refresh")
        self.assertEqual((eng.locals["te_dg_rate_new_b"], eng.locals["te_dg_rate_new_d"]),
                         (eng.vars["te_dg_mb"], eng.vars["te_dg_md"]))
        eng = self._eng(full=False)
        eng.modifiers["te_demog_census_births_down"] = 0.2
        eng.vars["te_dg_mb"] = -0.2
        eng.call("te_demog_rates_refresh")
        self.assertEqual((eng.locals["te_dg_rate_new_b"], eng.locals["te_dg_rate_new_d"]), (0, 0))
        eng = self._eng(stepped=0.0)
        eng.modifiers["te_demog_census_births_down"] = 0.2
        eng.vars["te_dg_mb"] = -0.2
        eng.call("te_demog_rates_refresh")
        self.assertEqual(eng.locals["te_dg_rate_new_b"], -0.2)

    def test_the_prior_term_needs_the_modifier(self):
        """A state that lost its modifier (a change of owner, an old save) keeps te_dg_mb: no phantom term."""
        eng = self._eng()
        eng.vars["te_dg_mb"] = -0.3
        eng.call("te_demog_rates_refresh")
        self.assertEqual(eng.locals["te_dg_rate_prev_b"], 0.0)

    def test_a_seed_leaves_the_rates_alone(self):
        eng = self._eng(stepped=0.0, cbr=0.0, cdr=0.0)
        eng.modifiers["te_demog_census_births_down"] = 0.2
        eng.vars["te_dg_mb"] = -0.2
        eng.call("te_demog_rates_refresh")
        self.assertEqual(eng.vars["te_dg_mb"], -0.2)
        self.assertEqual(eng.modifiers, {"te_demog_census_births_down": 0.2})

    def test_a_fresh_seed_gets_no_term(self):
        eng = self._eng(stepped=0.0, cbr=0.0, cdr=0.0)
        eng.call("te_demog_rates_refresh")
        self.assertNotIn("te_dg_mb", eng.vars)
        self.assertEqual(eng.modifiers, {})

    def test_nobody_gets_no_term(self):
        eng = self._eng(eb0=0.0, ed0=0.0, ebl=0.0)
        eng.call("te_demog_rates_refresh")
        self.assertNotIn("te_dg_mb", eng.vars)

    def test_display_only_clears_the_rates(self):
        eng = self._eng(full=False)
        eng.modifiers.update(te_demog_census_births_down=0.2, te_demog_census_deaths_up=0.1)
        eng.vars.update(te_dg_mb=-0.2, te_dg_md=0.1)
        eng.call("te_demog_rates_refresh")
        self.assertEqual(eng.modifiers, {})
        self.assertNotIn("te_dg_mb", eng.vars)
        self.assertNotIn("te_dg_md", eng.vars)

    def test_one_refresh_site(self):
        """Only te_demog_rates_apply adds or removes the census's modifiers, and only the two state-ROOT
        orchestrators call the refresh: the multiplier resolves against ROOT."""
        texts = {p: _text(p) for p in DEMOG_FILES}
        for name in ("te_demog_census_births_up", "te_demog_census_births_down", "te_demog_census_deaths_up",
                     "te_demog_census_deaths_down"):
            adders = [p.name for p, t in texts.items() if f"name = {name}" in t]
            self.assertEqual(adders, ["te_demog_rate_effects.txt"], name)
        callers = sorted(p.name for p, t in texts.items() if "te_demog_rates_refresh = yes" in t)
        self.assertEqual(callers, ["te_demog_effects.txt", "te_demog_fast_effects.txt"])
        self.assertIn("te_demog_rates_refresh = yes", _block(_text(EFFECTS), "te_demog_state_yearly"))
        self.assertIn("te_demog_rates_refresh = yes", _block(_text(FAST_EFFECTS), "te_demog_state_clock_step"))
        self.assertNotIn("te_demog_rates_refresh", _text(CONSOLE_EFFECTS))

    def test_the_refresh_comes_after_the_census_and_before_fast_mode(self):
        body = _block(_text(FAST_EFFECTS), "te_demog_state_clock_step")
        self.assertLess(body.index("te_demog_state_census = yes"), body.index("te_demog_rates_refresh = yes"))
        self.assertLess(body.index("te_demog_rates_refresh = yes"), body.index("te_demog_fast_refresh_rates = yes"))
        yearly = _block(_text(EFFECTS), "te_demog_state_yearly")
        self.assertLess(yearly.index("te_demog_state_census = yes"), yearly.index("te_demog_rates_refresh = yes"))

    def test_the_walk_sums_bare_births_by_literacy(self):
        body = _block(_text(EFFECTS), "te_demog_walks")
        self.assertIn("set_local_variable = { name = te_dg_w_ebl value = 0 }", body)
        self.assertIn("change_local_variable = { name = te_dg_w_ebl add = { value = local_var:te_dg_p_eb "
                      "multiply = literacy_rate } }", body)

    def test_the_census_modifiers_are_fixed_sign_unit_fields(self):
        mods = _raw_blocks([ROOT / "common" / "static_modifiers" / "te_demog_modifiers.txt"])
        for name, field, value in (("te_demog_census_births_up", "state_birth_rate_mult", "1"),
                                   ("te_demog_census_births_down", "state_birth_rate_mult", "-1"),
                                   ("te_demog_census_deaths_up", "state_mortality_mult", "1"),
                                   ("te_demog_census_deaths_down", "state_mortality_mult", "-1")):
            got = dict(re.findall(r"^\s*(\w+) = (\S+)", mods[name], re.M))
            got.pop("icon")
            self.assertEqual(got, {field: value}, name)


class _CountryEngine(_Engine):
    """_Engine plus the iterators and scope changes the country effects use. every_scope_war runs
    its body once per war in `wars` (the owner's dead in it, read through te_demog_war_dead_root);
    every_scope_state once per state in `states` (a dict of that state's variables, the locals
    staying shared); ordered_scope_state the best `max` of them by `order_by` (highest first,
    state_population read from the dict's own `state_population`); root = { } the country's
    variables, whatever scope is current. Variable
    lists live in `lists` (name -> the state dicts added), saved temporary scopes in `scopes` (a
    `scope:X` value is the state dict itself). A state's `owner = { }` trigger and `owner.X` read
    the country's variables (and fixtures); `any_scope_state` tests every state in `states`."""

    BLOCKS = ("every_scope_war", "every_scope_state", "ordered_scope_state", "root")

    def __init__(self, wars=(), states=(), **kwargs):
        super().__init__(**kwargs)
        self.wars, self.states = list(wars), list(states)
        self.root_vars = self.vars
        self.lists, self.scopes = {}, {}

    def number(self, tok):
        if tok.startswith("scope:"):
            return self.scopes[tok[6:]]
        if tok.startswith("owner."):
            saved, self.vars = self.vars, self.root_vars
            try:
                return self.number(tok[6:])
            finally:
                self.vars = saved
        return super().number(tok)

    def holds_in(self, scope_vars, items):
        saved, self.vars = self.vars, scope_vars
        try:
            return self.holds(items)
        finally:
            self.vars = saved

    def value_in(self, scope_vars, name):
        saved, self.vars = self.vars, scope_vars
        try:
            return self.value(name)
        finally:
            self.vars = saved

    def run(self, items):
        batch = []
        for item in items:
            if item[0] in self.BLOCKS or item[0] in ("clear_variable_list", "add_to_variable_list"):
                super().run(batch)
                batch = []
                if item[0] in self.BLOCKS:
                    self._iterate(item[0], item[2])
                elif item[0] == "clear_variable_list":
                    self.lists[item[2]] = []
                else:
                    assert self.vars is self.root_vars, "a list is added to from the country"
                    target = _find(item[2], "target")
                    assert target.startswith("scope:"), target
                    self.lists.setdefault(_find(item[2], "name"), []).append(self.scopes[target[6:]])
            else:
                batch.append(item)
        super().run(batch)

    def _test(self, key, op, arg):
        if key == "any_scope_state":
            return any(self.holds_in(state_vars, arg) for state_vars in self.states)
        if key == "has_variable_list":
            assert self.vars is self.root_vars, "a list is kept on the country"
            return arg in self.lists
        if key == "owner":
            return self.holds_in(self.root_vars, arg)
        return super()._test(key, op, arg)

    def _in(self, scope_vars, body):
        saved, self.vars = self.vars, scope_vars
        try:
            self.run(body)
        finally:
            self.vars = saved

    def _iterate(self, key, arg):
        if key == "root":
            return self._in(self.root_vars, arg)
        body = [i for i in arg if i[0] not in ("limit", "order_by", "max", "check_range_bounds",
                                                "save_temporary_scope_as")]
        if key == "every_scope_war":
            for dead in self.wars:
                self.fixtures["te_demog_war_dead_root"] = float(dead)
                self.run(body)
            return
        limit = next((v for k, _, v in arg if k == "limit"), [])
        chosen = []
        for state_vars in self.states:
            self.vars = state_vars
            try:
                if self.holds(limit):
                    chosen.append(state_vars)
            finally:
                self.vars = self.root_vars
        if key == "ordered_scope_state":
            def rank(state_vars):
                self.fixtures["state_population"] = state_vars.get("state_population", 0.0)
                saved, self.vars = self.vars, state_vars
                try:
                    return self.value(_find(arg, "order_by"))
                finally:
                    self.vars = saved
            chosen = sorted(chosen, key=rank, reverse=True)[:int(float(_find(arg, "max")))]
        for state_vars in chosen:
            if key == "ordered_scope_state":
                self.scopes[_find(arg, "save_temporary_scope_as")] = state_vars
            self._in(state_vars, body)


# the war-dead tests run the yearly effect without its census and Wealth Concentration (TestWealth's)
NO_CENSUS = {"te_demog_country_census": "", "te_demog_wc_war_shock": "", "te_demog_wc_national": ""}


class TestConcentrationRows(unittest.TestCase):
    def test_the_rows_check_the_states_owner_exists(self):
        """A state the national refresh chose can lose its owner before the next refresh: 'Event target
        link owner returned an invalid object' at te_demog_sguis.txt, read every frame the panel is open."""
        text = _text(ROOT / "common" / "scripted_guis" / "te_demog_sguis.txt")
        for sgui, var in (("te_demog_wc_top_sgui", "te_dg_wc_top"), ("te_demog_wc_bottom_sgui", "te_dg_wc_bottom")):
            shown = _block(text, sgui)
            self.assertRegex(shown, rf"var:{var} = {{\s*exists = owner\s*owner = ROOT\s*}}", sgui)


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

    def test_crisis_adds_devastation_as_a_share(self):
        """A state's devastation reads as a 0-1 share, as turmoil does (vanilla compares
        devastation > 0.1, >= 0.5; add_devastation takes points), so both are added as they are."""
        body = _block(_text(VALUES), "te_demog_crisis")
        self.assertRegex(body, r"add = devastation\b")
        self.assertNotIn("divide = 100", body)
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
        eng = _CountryEngine(wars=[100, 50], fixtures={}, triggers={"te_demog_cohorts_run": False})
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

    def month(self, eng, wars):
        eng.wars = wars
        eng.call("te_demog_country_monthly")

    def test_each_months_dead_go_to_states_by_their_soldiers(self):
        """Codex review on #830: the states take the dead month by month, so a state's step (on its
        own day) takes the dead of the same months as its population change; 31 December only
        clears the year's total after the war shock reads it."""
        states = self._states((300, 10000, True), (100, 30000, True), (600, 5000, False))
        states[0]["te_dg_war_in"] = 5.0   # an earlier share not yet taken is kept
        eng = _CountryEngine(states=states, fixtures={}, triggers={"te_demog_cohorts_run": True},
                             effects=NO_CENSUS)
        self.month(eng, [0])          # first run: the starting count
        self.month(eng, [600])
        self.assertEqual((states[0]["te_dg_war_in"], states[1]["te_dg_war_in"]), (5.0 + 450.0, 150.0))
        states[0].pop("te_dg_war_in")  # state 0 steps on its pulse and takes its share
        self.month(eng, [1000])
        self.assertEqual((states[0]["te_dg_war_in"], states[1]["te_dg_war_in"]), (300.0, 250.0))
        self.assertNotIn("te_dg_war_in", states[2], "a state with no census is skipped")
        self.assertEqual(eng.vars["te_dg_war_year"], 1000.0)
        eng.call("te_demog_country_yearly")
        self.assertEqual(eng.vars["te_dg_war_year"], 0.0)
        self.assertEqual((states[0]["te_dg_war_in"], states[1]["te_dg_war_in"]), (300.0, 250.0),
                         "31 December shares nothing more")

    def test_a_country_without_soldiers_shares_by_people(self):
        states = self._states((0, 10000, True), (0, 30000, True))
        eng = _CountryEngine(states=states, fixtures={}, triggers={"te_demog_cohorts_run": True})
        self.month(eng, [0])
        self.month(eng, [400])
        self.assertEqual((states[0]["te_dg_war_in"], states[1]["te_dg_war_in"]), (100.0, 300.0))

    def test_no_dead_or_no_rule_shares_nothing(self):
        for rule, wars in ((True, [0, 0]), (False, [0, 500])):
            states = self._states((300, 10000, True))
            eng = _CountryEngine(states=states, fixtures={}, triggers={"te_demog_cohorts_run": rule},
                                 effects=NO_CENSUS)
            for dead in wars:
                self.month(eng, [dead])
            self.assertNotIn("te_dg_war_in", states[0], (rule, wars))
            self.assertEqual(eng.vars["te_dg_war_year"], float(wars[-1]), (rule, wars))
            # the year's dead are cleared after the shock, so they are never shared out later
            eng.call("te_demog_country_yearly")
            self.assertEqual(eng.vars["te_dg_war_year"], 0.0, (rule, wars))
            self.assertNotIn("te_dg_war_in", states[0], (rule, wars))

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


class TestTrend(unittest.TestCase):
    """The arrows (Task 10): a figure's last-year value is kept, and its trend drawn, only when both
    the figure and the one before it came from a step. A seed writes 0 births and deaths, so a
    seed's CBR and CDR are no year to compare with."""

    INP = TestCohortScript.INP
    POP = 250000.0

    def stepped_engine(self):
        """A state seeded in 1836, with what its walk gives the step's flows (no residual, no crisis)."""
        eng = _engine_for(self.INP, 1836, self.POP)
        eng.call("te_demog_seed")
        eng.fixtures.update(te_demog_crisis=0.0, te_demog_family_transport=0.0)
        eng.vars.update(te_dg_eb=0.0, te_dg_ed=0.0, te_dg_fjob_share=0.3)
        return eng

    def step(self, eng, year):
        eng.fixtures["year"] = float(year)
        eng.vars["te_dg_pop_last"] = eng.vars["te_dg_people"]
        eng.call("te_demog_step")

    def seen(self, eng):
        return {k: eng.vars.get(k) for k in ("te_dg_trend_ok", "te_dg_stepped")}, \
            {k: k in eng.vars for k in ("te_dg_prev_median", "te_dg_prev_cbr", "te_dg_prev_tfr", "te_dg_prev_e0")}

    def test_state_arrows_come_from_the_second_step_on(self):
        eng = self.stepped_engine()
        flags, prev = self.seen(eng)
        self.assertEqual(flags, {"te_dg_trend_ok": 0.0, "te_dg_stepped": 0.0})
        self.assertFalse(any(prev.values()), "a seed has no last year")
        seed_tfr, seed_e0 = eng.vars["te_dg_tfr"], eng.vars["te_dg_e0"]
        self.step(eng, 1837)
        flags, prev = self.seen(eng)
        self.assertEqual(flags, {"te_dg_trend_ok": 0.0, "te_dg_stepped": 1.0}, "the year before it was a seed")
        self.assertFalse(any(prev.values()), "the seed's zero births are not kept as last year's CBR")
        self.assertGreater(eng.vars["te_dg_births"], 0)
        first_cbr, first_tfr, first_e0 = eng.vars["te_dg_cbr"], eng.vars["te_dg_tfr"], eng.vars["te_dg_e0"]
        self.step(eng, 1838)
        flags, prev = self.seen(eng)
        self.assertEqual(flags, {"te_dg_trend_ok": 1.0, "te_dg_stepped": 1.0})
        self.assertTrue(all(prev.values()))
        self.assertEqual(eng.vars["te_dg_prev_cbr"], first_cbr)
        self.assertEqual(eng.vars["te_dg_prev_tfr"], first_tfr)
        self.assertEqual(eng.vars["te_dg_prev_e0"], first_e0)
        self.assertGreater(first_cbr, 0, "the first step's CBR is real")
        # a re-seed (a census gap, an emptied ring) starts the sequence over
        eng.call("te_demog_seed")
        flags, _prev = self.seen(eng)
        self.assertEqual(flags, {"te_dg_trend_ok": 0.0, "te_dg_stepped": 0.0})
        self.step(eng, 1839)
        self.assertEqual(self.seen(eng)[0], {"te_dg_trend_ok": 0.0, "te_dg_stepped": 1.0})
        self.assertNotEqual(seed_tfr, 0)
        self.assertNotEqual(seed_e0, 0)

    def test_prepare_keeps_last_years_tfr_and_e0_only_after_a_step(self):
        """te_demog_prepare overwrites both, so the copy sits before it; Task 8 had none."""
        body = _block(_text(EFFECTS), "te_demog_prepare")
        self.assertLess(body.index("te_dg_prev_tfr"), body.index("te_demog_life_table"))
        self.assertLess(body.index("te_dg_prev_e0"), body.index("te_demog_life_table"))
        eng = _engine_for(self.INP, 1837, self.POP)
        eng.vars.update(te_dg_tfr=3.3, te_dg_e0=44.0, te_dg_stepped=0.0)
        eng.call("te_demog_prepare")
        self.assertFalse("te_dg_prev_tfr" in eng.vars)
        eng.vars.update(te_dg_tfr=3.3, te_dg_e0=44.0, te_dg_stepped=1.0)
        eng.call("te_demog_prepare")
        self.assertEqual((eng.vars["te_dg_prev_tfr"], eng.vars["te_dg_prev_e0"]), (3.3, 44.0))
        self.assertNotEqual(eng.vars["te_dg_tfr"], 3.3)

    def test_a_population_jump_reseeds(self):
        """A state merged or split moves its people by far more than a year's natural change. Over 25%
        since the last census the state's pulse seeds again (no migrants, the arrows start over)
        instead of stepping and counting the move as migration; a 3% rise is a year's step."""
        stubs = {"te_demog_walks": "", "te_inh_refresh_rural_effects": "", "te_demog_wc_state_yearly": "",
                 "te_inh_refresh_wc_state_effects": ""}
        for growth, reseeded in ((1.4, True), (0.6, True), (1.03, False)):
            with self.subTest(growth=growth):
                eng = _engine_for(self.INP, 1836, self.POP, effects=stubs)
                eng.call("te_demog_seed")
                eng.fixtures.update(te_demog_crisis=0.0, te_demog_family_transport=0.0)
                eng.vars.update(te_dg_eb=0.0, te_dg_ed=0.0, te_dg_fjob_share=0.3)
                self.step(eng, 1837)
                self.step(eng, 1838)
                self.assertEqual(self.seen(eng)[0], {"te_dg_trend_ok": 1.0, "te_dg_stepped": 1.0})
                people = eng.vars["te_dg_people"]
                eng.fixtures.update(year=1839.0, state_population=people * growth)
                eng.call("te_demog_state_yearly")
                self.assertEqual(eng.vars["te_dg_year"], 1839.0)
                self.assertAlmostEqual(eng.vars["te_dg_people"], people * growth)
                self.assertAlmostEqual(eng.vars["te_dg_pop_last"], people * growth)
                if reseeded:
                    self.assertEqual(self.seen(eng)[0], {"te_dg_trend_ok": 0.0, "te_dg_stepped": 0.0})
                    self.assertEqual(eng.vars["te_dg_births"], 0.0)
                    self.assertEqual(eng.vars["te_dg_net_migration"], 0.0, "no migrants")
                else:
                    self.assertEqual(self.seen(eng)[0], {"te_dg_trend_ok": 1.0, "te_dg_stepped": 1.0})
                    self.assertGreater(eng.vars["te_dg_births"], 0)
                    self.assertAlmostEqual(eng.vars["te_dg_net_migration"], 0.03 * people, delta=1.0)

    def test_fast_mode_skips_wealth_concentration_for_a_state_not_yet_walked(self):
        """Fast mode moves the walk to the clock's steps, but the yearly pulse still updates Wealth
        Concentration and inheritance's rural modifiers, which read the walk's sums. A state that appears between steps (a colony, a
        split) had none: 'Value of wrong type' at te_demog_wealth_effects.txt:64 and te_demog_values.txt,
        a few lines a game year in the 2026-10-10 fast run. It waits for its first walk."""
        stubs = {"te_demog_walks": "", "te_inh_refresh_wc_state_effects": "", "te_demog_state_census": "",
                 "te_demog_wc_state_yearly": "set_variable = { name = wc_ran value = 1 }",
                 "te_inh_refresh_rural_effects": "set_variable = { name = rural_ran value = 1 }"}
        for walked in (False, True):
            with self.subTest(walked=walked):
                eng = _Engine({}, triggers={"te_demog_clock_on": True}, effects=stubs)
                if walked:
                    eng.vars["te_dg_walk_pop"] = 1000.0
                eng.call("te_demog_state_yearly")
                # inheritance's rural modifiers read the walk's agrarian share (te_inheritance_effects.txt:251/258)
                self.assertEqual(("wc_ran" in eng.vars, "rural_ran" in eng.vars), (walked, walked))

    def test_a_seed_off_the_pulse_is_made_again_at_the_pulse(self):
        """Codex review on #830: game start and the console seed on a day that is not the state's
        pulse, so a step at the next pulse a year on would compare 12 to 24 months of change with a
        year's natural change. The state is marked, its first pulse seeds again (same year or not),
        and the step comes a year after that; a seed made on the pulse is not marked."""
        stubs = {"te_demog_walks": "", "te_inh_refresh_rural_effects": "", "te_demog_wc_state_yearly": "",
                 "te_inh_refresh_wc_state_effects": ""}
        for pulse_year in (1836, 1837):
            with self.subTest(pulse_year=pulse_year):
                eng = _engine_for(self.INP, 1836, self.POP, effects=stubs)
                eng.call("te_demog_seed_off_pulse")
                self.assertEqual(eng.vars["te_dg_reseed"], 1.0)
                eng.fixtures.update(te_demog_crisis=0.0, te_demog_family_transport=0.0)
                eng.vars.update(te_dg_eb=0.0, te_dg_ed=0.0, te_dg_fjob_share=0.3)
                eng.fixtures.update(year=float(pulse_year), state_population=self.POP * 1.02)
                eng.call("te_demog_state_yearly")
                self.assertNotIn("te_dg_reseed", eng.vars)
                self.assertEqual(eng.vars["te_dg_year"], float(pulse_year))
                self.assertEqual(eng.vars["te_dg_births"], 0.0, "seeded again, not stepped")
                self.assertAlmostEqual(eng.vars["te_dg_pop_last"], self.POP * 1.02)
                eng.fixtures.update(year=float(pulse_year + 1))
                eng.call("te_demog_state_yearly")
                self.assertGreater(eng.vars["te_dg_births"], 0, "a year on: the first step")
        eng = _engine_for(self.INP, 1836, self.POP, effects=stubs)
        eng.call("te_demog_seed")
        self.assertNotIn("te_dg_reseed", eng.vars, "a seed on the pulse is not marked")

    def test_off_pulse_seeds_are_marked(self):
        """Every seed made away from the state's own pulse goes through te_demog_seed_off_pulse."""
        self.assertIn("te_demog_seed_off_pulse = yes", _block(_text(EFFECTS), "te_demog_country_game_start"))
        console = _text(ROOT / "events" / "te_debug_demog_events.txt")
        self.assertIn("te_demog_seed_off_pulse = yes", console)
        self.assertNotIn("te_demog_seed = yes", console)
        body = _block(_text(EFFECTS), "te_demog_state_census")
        self.assertIn("has_variable = te_dg_reseed", body)

    def test_a_seed_zeroes_net_migration(self):
        """Only a step's flows write it, and the country sums it over every state with a census."""
        eng = _engine_for(self.INP, 1836, self.POP)
        eng.vars["te_dg_net_migration"] = 4000.0
        eng.vars["te_dg_mig_raw"] = 4000.0
        eng.call("te_demog_seed")
        self.assertEqual(eng.vars["te_dg_net_migration"], 0.0)
        self.assertEqual(eng.vars["te_dg_mig_raw"], 0.0)


class TestCountry(unittest.TestCase):
    def test_country_sums_skip_states_without_a_census(self):
        """Review Focus 1."""
        body = _block(_text(EFFECTS), "te_demog_country_census")
        for m in re.finditer(r"every_scope_state = \{", body):
            self.assertIn("te_demog_has_census = yes", body[m.end():m.end() + 200])
        self.assertIn("te_demog_country_lists = yes", body)
        lists = _block(_text(EFFECTS), "te_demog_country_lists")
        for m in re.finditer(r"ordered_scope_state = \{", lists):
            self.assertIn("te_demog_has_census = yes", lists[m.end():m.end() + 200])

    def test_the_country_sums_the_residual_before_the_noise_band(self):
        """The census log's gate check: moves between a country's own states cancel in this sum, which
        the floored te_dg_net_migration can't promise (a state's small loss is zeroed, a city's gain kept).
        A state loaded from a save made before te_dg_mig_raw existed has none until its next step."""
        body = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertIn("set_local_variable = { name = te_dg_c_mig_raw value = 0 }", body)
        add = body.index("change_local_variable = { name = te_dg_c_mig_raw add = var:te_dg_mig_raw }")
        self.assertLess(body.rindex("has_variable = te_dg_mig_raw", 0, add), add)
        self.assertIn("set_variable = { name = te_dg_mig_raw value = local_var:te_dg_c_mig_raw }", body)

    def test_a_revolutions_winner_gets_its_lists_back(self):
        """Review on #830: the winner inherits te_dg_census_year but no variable list, so the
        civil-war repair draws the lists again (behind the rule and a census) instead of leaving the
        States table empty until 31 December."""
        body = _block(_text(INH_EFFECTS), "inh_repair_after_civil_war")
        call = body.index("te_demog_country_lists = yes")
        self.assertLess(body.rindex("te_demog_cohorts_run = yes", 0, call), call)
        self.assertLess(body.rindex("has_variable = te_dg_census_year", 0, call), call)

    def test_projection_for_players_only(self):
        body = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertIn("is_ai = no", body[:body.index("te_demog_project = yes")])

    def test_the_census_is_wired_where_the_brief_puts_it(self):
        yearly = _block(_text(EFFECTS), "te_demog_country_yearly")
        self.assertNotIn("te_demog_share_war_dead", yearly, "the states take the war dead monthly")
        self.assertLess(yearly.index("te_demog_cohorts_run = yes"), yearly.index("te_demog_country_census = yes"))
        monthly = _block(_text(EFFECTS), "te_demog_country_monthly")
        self.assertLess(monthly.index("te_demog_cohorts_run = yes"), monthly.index("te_demog_share_war_dead = yes"))
        start = _block(_text(EFFECTS), "te_demog_country_game_start")
        self.assertLess(start.rindex("te_demog_cohorts_run = yes"), start.index("te_demog_country_census = yes"))
        self.assertGreater(start.index("te_demog_country_census = yes"), start.rindex("te_demog_seed_off_pulse = yes"))

    def test_the_city_ranking_script_value_is_negated(self):
        body = _block(_text(VALUES), "te_demog_neg_city_rank")
        self.assertIn("var:state_city_size_rank", body)
        self.assertRegex(body, r"multiply = -1")

    def test_squares_are_taken_in_units_of_100_000_people(self):
        """Values are i64 x 1e-5: the square of 10 million people is past the limit, and in millions the
        square of a state under ~3,200 urban people is under one unit (0.0032 squared); 100,000 keeps both."""
        body = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertRegex(body, r"var:te_dg_urban\s+divide = 100000\s")
        self.assertNotRegex(body, r"var:te_dg_urban\s+divide = 1000000")
        self.assertNotRegex(body, r"var:te_dg_urban\s+multiply = var:te_dg_urban")

    # -- the numbers, through the interpreter ---------------------------------------------------

    INPUTS = (   # (people, urban people, SoL, literacy): a big, a middling, a small state
        (4_000_000, 1_600_000, 22, 0.55),
        (1_500_000, 300_000, 14, 0.3),
        (600_000, 90_000, 9, 0.1),
    )

    @classmethod
    def setUpClass(cls):
        cls._three = [cls.state(*args, rank=r, migration=m)
                      for args, r, m in zip(cls.INPUTS, (12, 3, 40), (5000.0, -1200.0, 300.0))]

    @classmethod
    def state(cls, pop, urban, sol, literacy, rank=None, births=None, deaths=None, migration=0.0):
        """A state as a seed leaves it, with the figures a step would have given it."""
        inp = demographics_model.Inputs(sol=sol, literacy=literacy, urban_share=urban / pop,
                                        techs=frozenset({"medical_degrees"}),
                                        laws=frozenset({"law_women_in_the_fields"}))
        eng = _engine_for(inp, 1836, pop)
        eng.vars["te_dg_urban"] = float(urban)
        eng.call("te_demog_seed")
        v = eng.vars
        v["state_population"] = float(pop)
        if rank is not None:
            v["state_city_size_rank"] = float(rank)
        v["te_dg_births"] = births if births is not None else pop * 0.038
        v["te_dg_deaths"] = deaths if deaths is not None else pop * 0.031
        v["te_dg_net_migration"] = float(migration)
        v["te_dg_stepped"] = 1.0
        return v

    def three(self):
        return [dict(s) for s in self._three]

    def country(self, states, ai=False, fws=0.25, **kwargs):
        return _CountryEngine(states=states, fixtures={"year": 1900.0, "te_demog_female_work_share": fws},
                              triggers={"is_ai": ai, "te_demog_cohorts_run": True}, **kwargs)

    def test_figures_are_the_weighted_sums_of_the_census_states(self):
        states = self.three()
        nope = {"te_dg_people": 9e9, "te_dg_births": 9e9, "te_dg_urban": 9e9, "state_population": 9e9}   # no te_dg_year
        eng = self.country(states + [nope])
        eng.call("te_demog_country_census")
        v = eng.vars
        people = sum(s["te_dg_people"] for s in states)
        births, deaths = sum(s["te_dg_births"] for s in states), sum(s["te_dg_deaths"] for s in states)
        for b in range(18):
            for sex in "fm":
                self.assertAlmostEqual(v[f"te_dg_cb{sex}{b}"], sum(s[f"te_dg_b{sex}{b}"] for s in states), places=6)
        w = sum(s["te_dg_w1549"] for s in states)
        self.assertAlmostEqual(v["te_dg_w1549"], w, places=4)
        self.assertAlmostEqual(v["te_dg_tfr"], sum(s["te_dg_tfr"] * s["te_dg_w1549"] for s in states) / w, places=9)
        self.assertAlmostEqual(v["te_dg_e0"], sum(s["te_dg_e0"] * s["te_dg_people"] for s in states) / people, places=6)
        self.assertAlmostEqual(v["te_dg_e65"], sum(s["te_dg_e65"] * s["te_dg_people"] for s in states) / people,
                               places=6)
        self.assertAlmostEqual(v["te_dg_imr"], sum(s["te_dg_imr"] * s["te_dg_births"] for s in states) / births,
                               places=6)
        self.assertAlmostEqual(v["te_dg_cbr"], births * 1000 / people, places=9)
        self.assertAlmostEqual(v["te_dg_cdr"], deaths * 1000 / people, places=9)
        self.assertEqual(v["te_dg_net_migration"], 4100.0)
        self.assertEqual(v["te_dg_census_year"], 1900.0)
        # the shares and the median come from the country's bands, as a state's do
        total = sum(v[f"te_dg_cb{sex}{b}"] for sex in "fm" for b in range(18))
        young = sum(v[f"te_dg_cb{sex}{b}"] for sex in "fm" for b in range(3))
        old = sum(v[f"te_dg_cb{sex}{b}"] for sex in "fm" for b in range(13, 18))
        self.assertAlmostEqual(v["te_dg_young_share"], young / total, places=9)
        self.assertAlmostEqual(v["te_dg_old_share"], old / total, places=9)
        self.assertAlmostEqual(v["te_dg_working_share"], 1 - (young + old) / total, places=9)
        self.assertAlmostEqual(v["te_dg_dependency"], (young + old) / (total - young - old), places=9)
        self.assertTrue(15 < v["te_dg_median"] < 35)

    def test_urban_pattern(self):
        states = self.three()
        eng = self.country(states)
        eng.call("te_demog_country_census")
        v = eng.vars
        urban = [s["te_dg_urban"] / 1e5 for s in states]   # in units of 100,000 people
        people = sum(s["te_dg_people"] for s in states)
        self.assertAlmostEqual(v["te_dg_urban_share"], sum(urban) * 1e5 / people, places=9)
        self.assertAlmostEqual(v["te_dg_primacy"], max(urban) / sum(urban), places=9)
        self.assertAlmostEqual(v["te_dg_n_cities"], sum(urban) ** 2 / sum(u * u for u in urban), places=9)
        self.assertEqual(v["te_dg_urban_label"], 0.0, "1.6 of 1.99 million is Primate")
        self.assertAlmostEqual(v["te_dg_urban_share"], 1_990_000 / 6_100_000, places=9)
        self.assertFalse("te_dg_cities" in v, "te_dg_cities is the list of the three largest, not a number")

    def test_labels_by_primacy(self):
        """Primate from 40%, Dominant from 25%, Balanced from 10%, below it Dispersed (spec 5.1);
        the effective number of cities reads 1 for one state and n for n equal ones."""
        def pattern(urbans):
            states = []
            for u in urbans:
                s = dict(self._three[0])
                s["te_dg_urban"] = float(u) * 100_000
                states.append(s)
            eng = self.country(states)
            eng.call("te_demog_country_census")
            return eng.vars["te_dg_urban_label"], eng.vars["te_dg_primacy"], eng.vars["te_dg_n_cities"]
        for urbans, want in (((4, 6), 0.0), ((3, 3, 4), 0.0), ((3, 3, 3, 1), 1.0), ((1, 1, 1, 1), 1.0),
                             ((1,) * 8, 2.0), ((1,) * 10, 2.0), ((1,) * 11, 3.0), ((7,), 0.0)):
            self.assertEqual(pattern(urbans)[0], want, urbans)
        self.assertAlmostEqual(pattern((5,))[2], 1.0)
        self.assertAlmostEqual(pattern((2,) * 8)[2], 8.0)
        self.assertAlmostEqual(pattern((1, 3))[1], 0.75)
        self.assertEqual(pattern((0, 0))[0], 3.0, "no urban people: nothing to concentrate")

    def test_small_states_survive_the_engines_fixed_point(self):
        """Values are cut to five decimals after every operation. Ten states of 3,000 urban people are
        10 equal cities, 2,000 and 1,000 are 1.8 (3000^2 / (2000^2 + 1000^2)); in millions the squares
        were 9 and 4 and 1 units and the answers 90 and 0."""
        def pattern(urbans):
            states = []
            for u in urbans:
                s = dict(self._three[0])
                s["te_dg_urban"] = float(u)
                states.append(s)
            eng = self.country(states, ai=True, truncate=True)
            eng.call("te_demog_country_census")
            return eng.vars["te_dg_n_cities"], eng.vars["te_dg_primacy"]
        self.assertEqual(pattern((3000,) * 10)[0], 10.0)
        self.assertEqual(pattern((2000, 1000))[0], 1.8)
        self.assertAlmostEqual(pattern((2000, 1000))[1], 2 / 3, places=4)
        self.assertAlmostEqual(pattern((50_000_000, 30_000_000))[0], 80 ** 2 / (50 ** 2 + 30 ** 2), places=4)

    def test_the_lists(self):
        """te_dg_states: by the people the last census counted (the figure each row shows, not the
        live population), at most 40; te_dg_cities: the three largest cities by the global rank, a
        state with no rank or no census left out, a rank of 1 the largest. Each list is cleared
        only once it exists."""
        states = self.three()
        # the largest at its census, though fewer live today; no rank
        states.append(dict(states[0], te_dg_people=7e6, state_population=1e5))
        del states[3]["state_city_size_rank"]
        small = [dict(states[2], te_dg_people=float(1000 + i), state_population=float(1000 + i)) for i in range(45)]
        split = {"state_population": 9e6, "state_city_size_rank": 1.0}        # ranked, no walk or census yet
        eng = self.country(states + small + [split])
        self.assertNotIn("te_dg_cities", eng.lists, "the first census clears no list")
        eng.call("te_demog_country_census")
        listed = eng.lists["te_dg_states"]
        self.assertEqual(len(listed), 40)
        self.assertEqual([s["te_dg_people"] for s in listed[:4]], [7e6, 4e6, 1.5e6, 6e5])
        self.assertEqual([s["te_dg_people"] for s in listed[4:7]], [1044.0, 1043.0, 1042.0])
        cities = eng.lists["te_dg_cities"]
        self.assertEqual([s["state_city_size_rank"] for s in cities], [3.0, 12.0, 40.0])
        eng.call("te_demog_country_census")   # a refill, not an append
        self.assertEqual((len(eng.lists["te_dg_states"]), len(eng.lists["te_dg_cities"])), (40, 3))

    def test_projection_is_the_players(self):
        for ai in (False, True):
            states = self.three()
            eng = self.country(states, ai=ai)
            eng.call("te_demog_country_census")
            self.assertEqual("te_dg_pjf0" in eng.vars, not ai, f"ai={ai}")
            self.assertEqual("te_dg_pjm17" in eng.vars, not ai)
        v = eng.vars
        eng = self.country(self.three())
        eng.call("te_demog_country_census")
        v = eng.vars
        now = sum(v[f"te_dg_cb{sex}{b}"] for sex in "fm" for b in range(18))
        ahead = sum(v[f"te_dg_pj{sex}{b}"] for sex in "fm" for b in range(18))
        self.assertTrue(0.7 * now < ahead < 2.5 * now, (now, ahead))
        for sex in "fm":   # four five-year steps up: the children of now are the 20-year-olds of then
            ratio = v[f"te_dg_pj{sex}4"] / v[f"te_dg_cb{sex}0"]
            self.assertTrue(0.2 < ratio < 1.0, (sex, ratio))

    def test_projection_runs_on_the_models_own_tfr(self):
        """Phase 2 step 4: a state's te_dg_tfr is the realized figure (the model's x (1 + bz)) while the projection's
        mortality is the model's own (te_dg_m_*, unscaled), so the outline takes te_dg_tfr_model, weighted by
        women aged 15-49 as te_dg_tfr is. A state with none (an old save's, before its next step) gives its
        te_dg_tfr. The country's shown TFR stays the realized one."""
        states = self.three()
        for s, bz in zip(states, (0.3, -0.2)):
            s["te_dg_tfr_model"] = s["te_dg_tfr"]
            s["te_dg_tfr"] *= 1 + bz
        states[2].pop("te_dg_tfr_model", None)
        eng = self.country(states)
        eng.call("te_demog_country_census")
        w = sum(s["te_dg_w1549"] for s in states)
        shown = sum(s["te_dg_tfr"] * s["te_dg_w1549"] for s in states) / w
        model = sum(s.get("te_dg_tfr_model", s["te_dg_tfr"]) * s["te_dg_w1549"] for s in states) / w
        self.assertGreater(abs(shown - model), 0.1, "the case must tell the two apart")
        self.assertAlmostEqual(eng.vars["te_dg_tfr"], shown, places=6)
        self.assertAlmostEqual(eng.locals["te_dg_tfr"], model, places=6)

    def test_projection_reads_the_womens_work_share_from_the_states(self):
        """Any state of the country gives the owner's share; the work multiplier is split as
        te_demog_prepare does it, on the people-weighted average of the states' multipliers."""
        states = self.three()
        pm = sum(s["te_dg_people"] for s in states)
        work = sum(s["te_dg_m_work"] * s["te_dg_people"] for s in states) / pm
        for fws in (0.1, 0.45):
            eng = self.country([dict(s) for s in states], fws=fws)
            eng.call("te_demog_country_census")
            self.assertAlmostEqual(eng.locals["te_dg_fws"], fws)
            self.assertAlmostEqual(eng.locals["te_dg_m_work_f"], work * fws * 2, places=6)
            self.assertAlmostEqual(eng.locals["te_dg_m_work_m"], (1 - fws) * work * 2, places=6)
        body = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertNotIn("capital", body)

    def test_a_country_with_no_census_stays_pending(self):
        states = [{"te_dg_people": 5e5, "state_population": 5e5}]
        eng = self.country(states)
        eng.call("te_demog_country_census")
        self.assertFalse("te_dg_census_year" in eng.vars)
        self.assertFalse("te_dg_median" in eng.vars)
        self.assertFalse("te_dg_pjf0" in eng.vars)

    def test_the_country_keeps_last_years_figures_after_a_step_only(self):
        names = ("median", "young_share", "working_share", "old_share", "dependency", "sex_balance", "cbr", "cdr",
                 "w1549", "tfr", "e0", "e65", "imr", "net_migration", "urban_share", "primacy", "n_cities",
                 "urban_label")
        eng = self.country(self.three())
        eng.call("te_demog_country_census")
        self.assertEqual((eng.vars["te_dg_trend_ok"], eng.vars["te_dg_stepped"]), (0.0, 1.0),
                         "the first census: nothing before it")
        self.assertFalse(any(f"te_dg_prev_{n}" in eng.vars for n in names))
        first = {n: eng.vars[f"te_dg_{n}"] for n in names}
        eng.call("te_demog_country_census")   # the same states a year later, say
        self.assertEqual((eng.vars["te_dg_trend_ok"], eng.vars["te_dg_stepped"]), (1.0, 1.0))
        self.assertEqual({n: eng.vars[f"te_dg_prev_{n}"] for n in names}, first)

    def test_the_country_census_after_seeds_has_no_arrows(self):
        """1836: the game-start census and 31 December's both read seeded states (0 births), and
        the first stepped year's still has the seed's behind it."""
        seeds = self.three()
        for s in seeds:
            s["te_dg_births"] = s["te_dg_deaths"] = s["te_dg_net_migration"] = 0.0
            s["te_dg_stepped"] = 0.0
        eng = self.country(seeds)
        flags = []
        for rounds, born in ((2, False), (1, True), (1, True), (1, True)):
            for _ in range(rounds):
                if born:
                    for s in seeds:
                        s["te_dg_births"], s["te_dg_deaths"] = s["te_dg_people"] * 0.038, s["te_dg_people"] * 0.031
                eng.call("te_demog_country_census")
                flags.append((eng.vars["te_dg_trend_ok"], eng.vars["te_dg_stepped"]))
                if not born:   # no births: infant mortality is the states' by people, not 0
                    people = sum(s["te_dg_people"] for s in seeds)
                    self.assertAlmostEqual(eng.vars["te_dg_imr"],
                                           sum(s["te_dg_imr"] * s["te_dg_people"] for s in seeds) / people, places=6)
                    self.assertGreater(eng.vars["te_dg_imr"], 50)
        self.assertEqual(flags, [(0.0, 0.0), (0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)])
        self.assertAlmostEqual(eng.vars["te_dg_cbr"], 38.0, places=9)
        self.assertAlmostEqual(eng.vars["te_dg_prev_cbr"], 38.0, places=9)

    def test_imr_after_seeds_is_weighted_by_people(self):
        """A seed writes no births, so the births-weighted infant mortality would read 0: with none
        in the census the states' are weighted by people; with births, by births. CBR and CDR are 0
        while te_dg_stepped is 0, and that is no figure."""
        seeds = self.three()
        for s in seeds:
            s["te_dg_births"] = s["te_dg_deaths"] = s["te_dg_net_migration"] = 0.0
            s["te_dg_stepped"] = 0.0
        eng = self.country(seeds)
        eng.call("te_demog_country_census")
        by_people = sum(s["te_dg_imr"] * s["te_dg_people"] for s in seeds) / sum(s["te_dg_people"] for s in seeds)
        self.assertGreater(by_people, 50)
        self.assertAlmostEqual(eng.vars["te_dg_imr"], by_people, places=6)
        self.assertEqual((eng.vars["te_dg_cbr"], eng.vars["te_dg_cdr"], eng.vars["te_dg_stepped"]), (0.0, 0.0, 0.0))
        for s, rate in zip(seeds, (0.05, 0.03, 0.01)):
            s["te_dg_births"] = s["te_dg_people"] * rate
        eng.call("te_demog_country_census")
        by_births = sum(s["te_dg_imr"] * s["te_dg_births"] for s in seeds) / sum(s["te_dg_births"] for s in seeds)
        self.assertAlmostEqual(eng.vars["te_dg_imr"], by_births, places=6)
        self.assertNotAlmostEqual(by_births, by_people, places=3)

    def test_rates_divide_before_they_multiply(self):
        """A birth rate is births over people times 1,000; the other order forms births x 1,000, which a
        large state's births can carry past the engine's limit."""
        text = _text(EFFECTS)
        for name in ("te_demog_state_figures", "te_demog_country_census"):
            body = _block(text, name)
            for var in ("cbr", "cdr"):
                line = next(l for l in body.splitlines() if f"name = te_dg_{var} " in l)
                self.assertRegex(line, r"divide = \{[^}]*\} multiply = 1000 \}", line)
        line = next(l for l in _block(text, "te_demog_store_figures").splitlines() if "te_dg_sex_balance" in l)
        self.assertRegex(line, r"divide = \{[^}]*\} multiply = 100 \}", line)

    def test_game_start_ends_with_the_census(self):
        stubs = {"te_demog_walks": "", "te_demog_seed": "set_variable = { name = te_dg_year value = 1836 }",
                 "te_demog_country_census": "set_variable = { name = census_ran value = 1 }"}
        for rule in (True, False):
            states = [{}, {}]
            eng = _CountryEngine(states=states, fixtures={}, triggers={"te_demog_cohorts_run": rule}, effects=stubs)
            eng.call("te_demog_country_game_start")
            self.assertEqual(eng.vars.get("census_ran"), 1.0 if rule else None, rule)
            self.assertEqual(["te_dg_year" in s for s in states], [rule, rule])


BANKING = ROOT / "common" / "scripted_effects" / "banking_cycle_effects.txt"
CIVIL_WAR_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_civil_war_on_actions.txt"
APPLIED = {"te_inh_apply_concentration_modifiers": "set_variable = { name = applied value = var:te_inh_concentration }"}


class TestWealth(unittest.TestCase):
    """Wealth Concentration per state (Task 11; spec 4.2): each state's score drifts to its own
    target and takes the shocks; the country's figure, te_inh_concentration, is the states'
    average weighted by where property is held, and drives #822's two modifiers."""

    # -- the wiring ---------------------------------------------------------------------------------

    def test_national_figure_is_derived(self):
        """One effect on 31 December: the national figure, then the census reads it."""
        yearly = _block(_text(EFFECTS), "te_demog_country_yearly")
        self.assertLess(yearly.index("te_demog_wc_national = yes"), yearly.index("te_demog_country_census = yes"))
        self.assertNotIn("te_demog_wc_national", _block(_text(INH_EFFECTS), "te_inh_yearly_update"))
        self.assertIn("te_demog_wc_national = yes", _block(_text(INH_EFFECTS), "te_inh_shift_concentration"))
        self.assertIn("te_demog_wc_national = yes", _block(_text(INH_EFFECTS), "inh_repair_after_civil_war"))

    def test_shifts_reach_every_state(self):
        self.assertIn("every_scope_state", _block(_text(INH_EFFECTS), "te_inh_shift_concentration"))

    def test_one_refresh_site_for_the_modifiers(self):
        text = _text(WEALTH_EFFECTS)
        self.assertEqual(text.count("te_inh_apply_concentration_modifiers = yes"), 1)

    def test_drift_three_percent(self):
        self.assertIn("multiply = 0.03", _block(_text(WEALTH_EFFECTS), "te_demog_wc_state_yearly"))

    def test_wealth_runs_whatever_the_rule(self):
        """The pulse refreshes Wealth Concentration ungated; only the census it calls after checks the rule."""
        body = _block(_text(EFFECTS), "te_demog_state_yearly")
        self.assertNotIn("te_demog_cohorts_run", body)
        self.assertLess(body.index("te_demog_wc_state_yearly = yes"), body.index("te_demog_state_census = yes"))
        self.assertIn("te_demog_cohorts_run = yes", _block(_text(EFFECTS), "te_demog_state_census"))

    def test_the_war_shock_and_the_war_dead_run_whatever_the_rule(self):
        yearly = _block(_text(EFFECTS), "te_demog_country_yearly")
        self.assertLess(yearly.index("te_demog_wc_war_shock = yes"), yearly.index("te_demog_cohorts_run = yes"))
        reset = yearly.index("set_variable = { name = te_dg_war_year value = 0 }")
        self.assertLess(yearly.index("te_demog_wc_war_shock = yes"), reset)
        self.assertNotIn("te_demog_cohorts_run", yearly[:reset], "the reset runs whatever the rule")

    def test_822s_drift_only_without_a_scored_state(self):
        body = _block(_text(INH_EFFECTS), "te_inh_yearly_update")
        guard = body.index("NOT = { any_scope_state = { has_variable = te_dg_wc } }")
        self.assertLess(guard, body.index("te_inh_concentration_next"))
        self.assertLess(guard, body.index("te_inh_apply_concentration_modifiers = yes"))
        for call in ("te_inh_tidy_amendments = yes", "te_inh_count_duty_years = yes"):
            self.assertRegex(body, rf"(?m)^\t{call}$", "every country, scored or not")

    def test_822s_target_follows_the_states(self):
        text = _text(INH_VALUES)
        body = _block(text, "te_inh_concentration_target")
        self.assertIn("value = te_inh_law_amendment_target", body)
        self.assertIn("value = var:te_dg_wc_target", body)
        laws = _block(text, "te_inh_law_amendment_target")
        self.assertIn("amendment_perpetual_trusts", laws)
        self.assertNotIn("te_inh_title_continuity", laws, "the pin is the states' and the display's, not the law's")

    def test_the_shown_target_follows_a_law_change_at_once(self):
        """Review on #830: the stored national target is summed on 31 December, but a law or a tax
        on wealth moves every state's target alike, so the shown target moves by the change since
        then; continuity of title still pins it at the score."""
        cases = (
            # law now, tax now, pinned -> shown
            (75.0, -5.0, False, 60.0),   # nothing changed since the refresh
            (85.0, -5.0, False, 70.0),   # the law term rose by 10
            (75.0, 0.0, False, 65.0),    # Graduated Taxation repealed: +5
            (100.0, 0.0, False, 90.0),
            (40.0, -5.0, False, 25.0),
            (5.0, -10.0, False, 0.0),    # clamped at 0
            (85.0, -5.0, True, 33.0),    # continuity of title: the score
        )
        for law, tax, pinned, shown in cases:
            eng = _CountryEngine(fixtures={"te_inh_law_amendment_target": law, "te_demog_wc_tax_term": tax})
            eng.values.update(_raw_blocks([INH_VALUES]))
            eng.fixtures["te_inh_law_amendment_target"] = law
            eng.vars.update(te_dg_wc_target=60.0, te_dg_wc_t_law=25.0, te_dg_wc_t_tax=-5.0, te_inh_concentration=33.0)
            if pinned:
                eng.vars["te_inh_title_continuity"] = 1.0
            eng.run(_parse_script("set_variable = { name = shown value = te_inh_concentration_target }"))
            self.assertAlmostEqual(eng.vars["shown"], shown, msg=(law, tax, pinned))

    def test_game_start_seeds_every_state_then_the_national_figure(self):
        body = _block(_text(INH_EFFECTS), "te_inh_game_start")
        self.assertLess(body.index("te_demog_walks = yes"), body.index("te_demog_wc_seed_state = yes"))
        self.assertLess(body.index("te_demog_wc_seed_state = yes"), body.index("te_demog_wc_national = yes"))
        self.assertNotIn("name = te_inh_concentration", body)

    def test_every_change_to_a_score_ends_clamped(self):
        for path in (WEALTH_EFFECTS, INH_EFFECTS):
            for name, body in _raw_blocks([path]).items():
                ops = re.findall(r"(change|clamp)_variable = \{\s*name = te_dg_wc\b", body)
                if ops:
                    self.assertEqual(ops[-1], "clamp", name)

    def test_devastation_is_a_share(self):
        """A state's devastation reads as a 0-1 share: a fully devastated state (1) loses 10 points a year."""
        body = _block(_text(WEALTH_EFFECTS), "te_demog_wc_state_yearly")
        self.assertIn("add = { value = devastation multiply = -10 }", body)

    def test_the_shocks_are_wired(self):
        on_actions = _text(DEMOG_ON_ACTIONS)
        self.assertIn("te_demog_lost_war", _block(on_actions, "on_lost_war"))
        lost = _block(on_actions, "te_demog_lost_war")
        self.assertIn("te_demog_wc_shock = { AMOUNT = -5 }", lost)
        self.assertNotIn("te_demog_cohorts_run", lost)
        # owner's ruling on #830: only a loser a war goal was enforced against
        self.assertLess(lost.index("exists = scope:victim_of_wargoal"), lost.index("te_demog_wc_shock"))
        banking = _text(BANKING)
        sites = [m.end() for m in re.finditer(r"set_variable = \{ name = banking_crisis_wave_crashed value = 1 \}", banking)]
        self.assertEqual(len(sites), 2)
        for end in sites:
            self.assertIn("te_demog_wc_shock = { AMOUNT = -5 }", banking[end:end + 300])

    def test_a_won_left_revolution_reads_the_resolved_sides(self):
        """The repair runs between te_civil_war_resolve_sides and te_civil_war_clear (which removes
        te_cw_origin; a loyalist winner can carry the rebels' te_cw_origin), so it reads
        te_cw_rebels_won, and the national figure follows the shock."""
        civil = _block(_text(WEALTH_EFFECTS), "te_demog_wc_civil_war_won")
        self.assertIn("var:te_cw_rebels_won = 1", civil)
        self.assertIn("AMOUNT = -20", civil)
        self.assertNotIn("te_cw_origin", civil)
        repair = _block(_text(INH_EFFECTS), "inh_repair_after_civil_war")
        self.assertLess(repair.index("te_demog_wc_civil_war_won = yes"), repair.index("te_demog_wc_national = yes"))
        self.assertIn("inh_repair_after_civil_war = yes", _block(_text(CIVIL_WAR_ON_ACTIONS), "te_civil_war_on_won"))

    # -- a state's score and target, through the interpreter --------------------------------------------

    def state_year(self, state, owner=None, devastation=0.0, target=60.0):
        eng = _CountryEngine(states=[state], fixtures={"te_demog_wc_target": target, "devastation": devastation})
        eng.vars.update(owner or {})
        eng._in(state, _parse_script("te_demog_wc_state_yearly = yes"))
        return state

    def test_a_state_closes_three_percent_of_the_gap(self):
        self.assertAlmostEqual(self.state_year({"te_dg_wc": 40.0})["te_dg_wc"], 40.6)
        self.assertAlmostEqual(self.state_year({"te_dg_wc": 80.0}, target=20.0)["te_dg_wc"], 78.2)
        self.assertEqual(self.state_year({"te_dg_wc": 40.0})["te_dg_wc_target"], 60.0)

    def test_devastation_destroys_local_capital(self):
        self.assertAlmostEqual(self.state_year({"te_dg_wc": 40.0}, devastation=0.5)["te_dg_wc"], 35.6)
        self.assertEqual(self.state_year({"te_dg_wc": 3.0}, devastation=1.0, target=0.0)["te_dg_wc"], 0.0)

    def test_a_state_without_a_score_starts_at_its_owners_figure(self):
        self.assertEqual(self.state_year({}, owner={"te_inh_concentration": 72.0})["te_dg_wc"], 72.0)
        self.assertEqual(self.state_year({})["te_dg_wc"], 60.0, "an owner with no figure: the state's target")

    def test_the_seed_starts_a_state_at_its_target(self):
        state = {}
        eng = _CountryEngine(states=[state], fixtures={"te_demog_wc_target": 55.0})
        eng._in(state, _parse_script("te_demog_wc_seed_state = yes"))
        self.assertEqual((state["te_dg_wc"], state["te_dg_wc_target"]), (55.0, 55.0))

    def target(self, state, owner=None, law=80.0, land=6.0, tax=-5.0, econ=0.0):
        eng = _CountryEngine(states=[state], fixtures={"te_inh_law_amendment_target": law,
                                                       "te_demog_wc_land_term": land, "te_demog_wc_tax_term": tax,
                                                       "te_demog_wc_econ_term": econ})
        eng.vars.update(owner or {})
        return eng.value_in(state, "te_demog_wc_target")

    def test_the_target_sums_its_terms(self):
        state = {"te_dg_lv_priv": 30.0, "te_dg_lv_self": 10.0, "te_dg_lv_ctry": 0.0, "te_dg_gini": 0.5}
        # law 80, land 6, ownership (30/40 - 0.65) x 40 = 4, inequality (0.5 - 0.40) x 40 = 4, taxes -5
        self.assertAlmostEqual(self.target(state), 89.0)
        self.assertAlmostEqual(self.target(state, econ=-10.0), 79.0, msg="the economic laws add in")
        self.assertEqual(self.target(state, law=100.0, land=15.0), 100.0)
        self.assertEqual(self.target(state, law=0.0, land=-20.0), 0.0)

    def test_the_inequality_term_is_four_points_a_tenth_above_040(self):
        # owner, 2026-10-10: on the shown Gini, +40 x (Gini - 0.40), at most +15 (from 0.775); the shown
        # figure is at least 0.30, so at least -4 (= 28 x (computed - 0.143), close to 30 x (computed - 0.15))
        for gini, term in ((0.4, 0.0), (0.5, 4.0), (0.6, 8.0), (0.775, 15.0), (0.9, 15.0), (0.3, -4.0)):
            state = {"te_dg_lv_priv": 0.4, "te_dg_lv_self": 0.0, "te_dg_lv_ctry": 0.0, "te_dg_gini": gini}
            self.assertAlmostEqual(self.target(state, law=50.0, land=0.0, tax=0.0), 50 + term, msg=str(gini))

    def test_the_ownership_and_inequality_terms_are_capped(self):
        private = {"te_dg_lv_priv": 50.0, "te_dg_lv_self": 0.0, "te_dg_lv_ctry": 0.0, "te_dg_gini": 0.9}
        # centred on 1836's measured 0.65 private: all private is +14, the most the term can add
        self.assertAlmostEqual(self.target(private, law=50.0, land=0.0, tax=0.0), 50 + 14 + 15)
        two_thirds = {"te_dg_lv_priv": 65.0, "te_dg_lv_self": 30.0, "te_dg_lv_ctry": 5.0, "te_dg_gini": 0.4}
        self.assertAlmostEqual(self.target(two_thirds, law=50.0, land=0.0, tax=0.0), 50.0, msg="1836's mix: no term")
        state_owned = {"te_dg_lv_priv": 0.0, "te_dg_lv_self": 5.0, "te_dg_lv_ctry": 45.0, "te_dg_gini": 0.3}
        # the shown Gini is at least 0.30, so the inequality term is at least -4 (owner: a shallow bottom)
        self.assertAlmostEqual(self.target(state_owned, law=50.0, land=0.0, tax=0.0), 50 - 20 - 4)
        no_capital = {"te_dg_lv_priv": 0.4, "te_dg_lv_self": 0.0, "te_dg_lv_ctry": 0.0, "te_dg_gini": 0.4}
        self.assertAlmostEqual(self.target(no_capital, law=50.0, land=0.0, tax=0.0), 50.0, msg="no capital: no term")

    def test_continuity_of_title_pins_the_target_at_the_score(self):
        state = {"te_dg_lv_priv": 30.0, "te_dg_lv_self": 10.0, "te_dg_lv_ctry": 0.0, "te_dg_gini": 0.5,
                 "te_dg_wc": 33.0}
        self.assertEqual(self.target(state, owner={"te_inh_title_continuity": 1.0}), 33.0)
        self.assertAlmostEqual(self.target(state), 89.0)

    # -- the national figure, through the interpreter ------------------------------------------------

    @staticmethod
    def scored(wc, target, own=0.0, coop=0.0, ctry=0.0, bur=0.0, pop=1e6, gini=0.4, priv=10.0,
               bands=None, layout=P.GINI_LAYOUT):
        """A scored state; its walk stored the bands it has people in, under `layout` (None: a state
        from a save before the layout marker, which has no te_dg_gini_layout)."""
        state = {"te_dg_wc": float(wc), "te_dg_wc_target": float(target), "te_dg_lv_own": float(own),
                 "te_dg_lv_self": float(coop), "te_dg_lv_ctry": float(ctry), "te_dg_lv_priv": float(priv),
                 "te_dg_bureaucrats": float(bur), "te_dg_walk_pop": float(pop), "te_dg_gini": float(gini)}
        bands = {1: (900, 1350), 5: (90, 270), 10: (10, 150)} if bands is None else bands
        for k, (n, y) in bands.items():
            state[f"te_dg_gn{k}"], state[f"te_dg_gy{k}"] = float(n), float(y)
        if layout is not None:
            state["te_dg_gini_layout"] = float(layout)
        return state

    @staticmethod
    def national(states, **country):
        eng = _CountryEngine(states=states, effects=APPLIED,
                             fixtures={"te_inh_law_amendment_target": 75.0, "te_demog_wc_land_term": 4.0,
                                       "te_demog_wc_tax_term": -5.0, "te_demog_wc_econ_term": 5.0})
        eng.vars.update(country)
        eng.call("te_demog_wc_national")
        return eng.vars

    def test_the_national_figure_weighs_states_by_property(self):
        a = self.scored(80, 70, own=30, ctry=40, bur=900, gini=0.5, priv=400,
                        bands={k: (1e5 / k + k, (1e5 / k + k) * 3 * k) for k in range(1, P.GINI_BANDS + 1)})
        b = self.scored(40, 50, coop=10, ctry=60, bur=100, gini=0.3, priv=200,
                        bands={k: (7e4 / k + 2 * k, (7e4 / k + 2 * k) * (2.5 * k + 1)) for k in range(1, P.GINI_BANDS + 1)})
        c = {"te_dg_walk_pop": 9e9, "te_dg_lv_own": 9e9}   # no score: left out
        v = self.national([a, b, c])
        # 100 state-owned levels where 1,000 bureaucrats work: a holds 900 of them, b 100
        wa, wb = 30 + 0.9 * 100 * 0.1, 10 + 0.1 * 100 * 0.1
        mean = lambda x, y: (x * wa + y * wb) / (wa + wb)   # noqa: E731
        self.assertAlmostEqual(v["te_inh_concentration"], mean(80, 40))
        # each state's target is rewritten from the law and taxes as they stand (the fixture's
        # 70 and 50 are stale), and the national target is their weighted mean
        self.assertNotEqual((a["te_dg_wc_target"], b["te_dg_wc_target"]), (70.0, 50.0))
        self.assertAlmostEqual(v["te_dg_wc_target"], mean(a["te_dg_wc_target"], b["te_dg_wc_target"]))
        self.assertEqual(v["applied"], v["te_inh_concentration"], "the modifiers read this year's figure")
        self.assertAlmostEqual(v["te_dg_wc_t_law"], 25.0)
        self.assertAlmostEqual(v["te_dg_wc_t_land"], 4.0)
        own_a, own_b = (400 / 440 - 0.65) * 40, (200 / 270 - 0.65) * 40   # +10.36 and +3.63: inside the caps
        self.assertTrue(-20 < own_b < own_a < 20)
        self.assertAlmostEqual(v["te_dg_wc_t_own"], mean(own_a, own_b))
        self.assertAlmostEqual(v["te_dg_wc_t_ineq"], mean(4, -4))
        self.assertAlmostEqual(v["te_dg_wc_t_tax"], -5.0)
        self.assertAlmostEqual(v["te_dg_wc_t_econ"], 5.0)
        # with no state clamped, the six bars add up to the target above them
        bars = sum(v[f"te_dg_wc_t_{t}"] for t in ("law", "land", "own", "ineq", "tax", "econ"))
        self.assertAlmostEqual(v["te_dg_wc_target"], 50 + bars)
        self.assertIs(v["te_dg_wc_top"], a)
        self.assertIs(v["te_dg_wc_bottom"], b)
        bands = [(a.get(f"te_dg_gn{k}", 0) + b.get(f"te_dg_gn{k}", 0), a.get(f"te_dg_gy{k}", 0) + b.get(f"te_dg_gy{k}", 0))
                 for k in range(1, P.GINI_BANDS + 1)]
        expected = demographics_model.shown_gini(demographics_model.grouped_gini(bands))
        self.assertAlmostEqual(v["te_dg_gini"], expected, places=9, msg="the Gini of the summed bands")

    def test_a_state_from_an_old_save_adds_no_bands(self):
        # Review Focus 1: before its own pulse a state has only the old strata sums
        old = self.scored(60, 55, bands={}, layout=None)
        old.update(te_dg_n_lo=900.0, te_dg_y_lo=1350.0)
        new = self.scored(40, 50, bands={2: (900e3, 12.0), 9: (1e4, 2.0)})
        v = self.national([old, new])
        want = demographics_model.shown_gini(demographics_model.grouped_gini([(900e3, 12.0), (1e4, 2.0)]))
        self.assertAlmostEqual(v["te_dg_gini"], want, places=9)

    def test_a_state_with_the_old_fourteen_bands_adds_none(self):
        """A save from before the layout marker (2026-10-10): 14 bands, the last one 61 or more, income
        capped at 60 and summed in other units. Until its own pulse such a state adds nothing (its band 14
        is not the new band 14, and it has no 15th), so no sum mixes the two layouts."""
        fourteen = {k: (1e4 * k, 1e4 * k * 9.0 * k) for k in range(1, 15)}
        old = self.scored(60, 55, bands=fourteen, layout=None)
        new = self.scored(40, 50, bands={2: (900e3, 12.0), 30: (1e3, 9e3)})
        v = self.national([old, new])
        want = demographics_model.shown_gini(demographics_model.grouped_gini([(900e3, 12.0), (1e3, 9e3)]))
        self.assertAlmostEqual(v["te_dg_gini"], want, places=9)
        # a marker of another layout is skipped the same way
        self.assertNotIn("te_dg_gini", self.national([self.scored(60, 55, bands=fourteen, layout=1)]))

    def test_a_country_whose_states_have_no_bands_keeps_its_gini(self):
        # an old save, before any of its states' pulses: no band sums, so no new figure (not 0.00)
        old = self.scored(60, 55, bands={}, layout=None)
        v = self.national([old], te_dg_gini=0.42)
        self.assertEqual(v["te_dg_gini"], 0.42)
        old14 = self.scored(60, 55, bands={k: (10.0, 20.0 * k) for k in range(1, 15)}, layout=None)
        self.assertEqual(self.national([old14], te_dg_gini=0.42)["te_dg_gini"], 0.42)

    def test_scored_states_without_bands_give_a_target_but_no_gini(self):
        """The national figure writes the Gini only from states that have wealth bands, but the
        target (the panel's old gate) from any scored state. A country whose scored states have
        no bands yet (a save from before the bands, a state scored before its first walk) thus has
        the one and not the other, and a panel that reads the Gini under the target's gate
        shows 0.00 (a missing variable reads 0). The panel gates the Gini on te_dg_gini itself."""
        old = self.scored(60, 55, bands={}, layout=None)
        v = self.national([old])
        self.assertIn("te_dg_wc_target", v, "the target is written: the old gate is open")
        self.assertIn("te_inh_concentration", v)
        self.assertNotIn("te_dg_gini", v, "no state has bands, so there is no Gini to show")
        # once one state has bands the same call writes the Gini beside the target
        new = self.scored(40, 50, bands={2: (900e3, 12.0), 9: (1e4, 2.0)})
        self.assertIn("te_dg_gini", self.national([old, new]))

    def test_the_bureaucrat_share_multiplies_before_it_divides(self):
        """A state with a tiny share of the bureaucrats keeps its precision: values are i64 x 1e-5."""
        body = _block(_text(WEALTH_EFFECTS), "te_demog_wc_national")
        weight = body[body.index("value = var:te_dg_bureaucrats"):]
        self.assertLess(weight.index("multiply = local_var:te_dg_wc_ctry"),
                        weight.index("divide = { value = local_var:te_dg_wc_bur min = 1 }"))

    def test_without_property_the_states_weigh_by_people(self):
        v = self.national([self.scored(80, 70, pop=2e6), self.scored(40, 50, pop=1e6, ctry=30)])
        self.assertAlmostEqual(v["te_inh_concentration"], (80 * 2 + 40) / 3, msg="state-owned levels, no bureaucrats")
        v = self.national([self.scored(80, 70, pop=0), self.scored(40, 50, pop=0)])
        self.assertAlmostEqual(v["te_inh_concentration"], 60.0, msg="no people either: one each")

    def test_a_country_with_no_scored_state_keeps_its_own_figure(self):
        v = self.national([{"te_dg_walk_pop": 1e5}], te_inh_concentration=63.0)
        self.assertEqual((v["te_inh_concentration"], v["applied"]), (63.0, 63.0))
        for name in ("te_dg_wc_target", "te_dg_gini", "te_dg_wc_top", "te_dg_wc_t_law"):
            self.assertNotIn(name, v)
        self.assertNotIn("applied", self.national([]), "no figure: no modifiers")

    def test_a_shock_moves_every_score_then_the_national_figure(self):
        a, b = self.scored(80, 70, own=10), self.scored(3, 50, own=10)
        eng = _CountryEngine(states=[a, b, {}], effects=APPLIED,
                             fixtures={"te_inh_law_amendment_target": 75.0, "te_demog_wc_land_term": 4.0,
                                       "te_demog_wc_tax_term": -5.0, "te_demog_wc_econ_term": 5.0})
        eng.run(_parse_script("te_demog_wc_shock = { AMOUNT = -5 }"))
        self.assertEqual((a["te_dg_wc"], b["te_dg_wc"]), (75.0, 0.0))
        self.assertAlmostEqual(eng.vars["te_inh_concentration"], 37.5)

    def test_a_shock_reaches_a_country_with_no_scored_state(self):
        """An old save before its states' first pulse, or a landless country: the shock lands on its own
        figure, clamped, and the modifiers follow; with no figure yet it starts from #822's target."""
        for before, amount, after in ((63.0, -5, 58.0), (3.0, -5, 0.0), (98.0, 5, 100.0), (None, -20, 30.0)):
            states = [{"te_dg_walk_pop": 1e5}]
            eng = _CountryEngine(states=states, effects=APPLIED, fixtures={"te_inh_concentration_target": 50.0})
            if before is not None:
                eng.vars["te_inh_concentration"] = before
            eng.run(_parse_script(f"te_demog_wc_shock = {{ AMOUNT = {amount} }}"))
            self.assertEqual((eng.vars["te_inh_concentration"], eng.vars["applied"]), (after, after), before)
            self.assertNotIn("te_dg_wc", states[0])

    # -- the war shock on 31 December -----------------------------------------------------------------

    def war_year(self, states, at_war, dead, shocks=None, rule=False):
        eng = _CountryEngine(states=states, fixtures={"total_population": 1e6},
                             triggers={"te_demog_cohorts_run": rule, "is_at_war": at_war},
                             effects={"te_demog_wc_national": "", "te_demog_country_census": ""})
        eng.vars["te_dg_war_year"] = float(dead)
        if shocks is not None:
            eng.vars["te_dg_war_shock"] = float(shocks)
        eng.call("te_demog_country_yearly")
        return eng.vars

    def test_a_year_of_heavy_war_dead_lowers_every_score(self):
        states = [{"te_dg_wc": 50.0}, {"te_dg_wc": 0.5}, {}]
        v = self.war_year(states, True, 2500)   # 0.25% of a million
        self.assertEqual([s.get("te_dg_wc") for s in states], [49.0, 0.0, None])
        self.assertEqual(v["te_dg_war_shock"], 1.0)
        self.assertEqual(v["te_dg_war_year"], 0.0, "the census is off: the dead are cleared after the shock")

    def test_light_war_dead_or_ten_shocks_already_do_nothing(self):
        for dead, shocks in ((1500, None), (2500, 10)):
            states = [{"te_dg_wc": 50.0}]
            v = self.war_year(states, True, dead, shocks)
            self.assertEqual(states[0]["te_dg_wc"], 50.0, (dead, shocks))
            self.assertEqual(v["te_dg_war_shock"], 0.0 if shocks is None else 10.0)

    def test_peace_ends_the_count(self):
        states = [{"te_dg_wc": 50.0}]
        v = self.war_year(states, False, 9000, shocks=4)
        self.assertNotIn("te_dg_war_shock", v)
        self.assertEqual(states[0]["te_dg_wc"], 50.0)


INH_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_inheritance_modifiers.txt"
INH_EVENTS = ROOT / "events" / "inheritance_events.txt"
STATE_WC_MODIFIERS = ("inh_concentrated_property", "inh_dispersed_property", "inh_land_hunger")
STATE_WC_MULTS = ("te_inh_wc_high_mult", "te_inh_wc_low_mult", "te_inh_land_hunger_mult")


SGUIS = ROOT / "common" / "scripted_guis" / "te_demog_sguis.txt"
MISC_LOC = ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml"


class TestGiniGate(unittest.TestCase):
    """The panel reads the country's Gini (te_dg_gini) only under a gate on that variable. It used
    to read it under te_demog_wealth_ready_sgui, which asks for te_dg_wc_target, written under a
    wider condition (any scored state, not any state with wealth bands): with the target and no
    Gini, a .gui read of the missing variable showed 0.00, which reads as perfect equality."""

    def test_the_gini_gate_asks_for_the_gini(self):
        gate = _block(_text(SGUIS), "te_demog_gini_ready_sgui")
        self.assertRegex(gate, r"scope = country\b")
        shown = re.search(r"is_shown = \{([^{}]*)\}", gate)
        self.assertIsNotNone(shown)
        self.assertEqual(shown.group(1).split(), ["has_variable", "=", "te_dg_gini"])
        # the Wealth Concentration gate is unchanged: it still asks for the target
        wealth = re.search(r"is_shown = \{([^{}]*)\}", _block(_text(SGUIS), "te_demog_wealth_ready_sgui"))
        self.assertEqual(wealth.group(1).split(), ["has_variable", "=", "te_dg_wc_target"])

    def test_every_country_gini_the_gui_shows_is_picked_by_the_gini_gate(self):
        gui, loc = _text(DEMOG_GUI), _text(MISC_LOC)
        # the loc keys that read the country's Gini
        keys = re.findall(r'^ (\w+):0 "[^"\n]*GetPlayer\.MakeScope\.Var\(\'te_dg_gini\'\)', loc, re.M)
        self.assertEqual(sorted(keys), ["te_demog_gini_value", "te_demog_ov_gini_value"])
        gate = r"GetScriptedGui\('te_demog_gini_ready_sgui'\)\.IsShown\( GuiScope\.SetRoot\( GetPlayer\.MakeScope \)\.End \)"
        for key in keys:
            uses = [m.start() for m in re.finditer(rf"['\"]{key}['\"]", gui)]
            self.assertTrue(uses, f"{key} is not used")
            for at in uses:
                line = gui[gui.rfind("\n", 0, at) + 1:gui.index("\n", at)]
                self.assertRegex(line, rf"SelectLocalization\( {gate}, '{key}', '\w+' \)", f"{key} is shown bare: {line.strip()}")

    def test_the_gini_cell_has_a_pending_text(self):
        gui, loc = _text(DEMOG_GUI), _text(MISC_LOC)
        pending = re.search(r"GetScriptedGui\('te_demog_gini_ready_sgui'\)[^\n]*'te_demog_gini_value', '(\w+)'", gui)
        self.assertIsNotNone(pending)
        self.assertRegex(loc, rf"(?m)^ {pending.group(1)}:0 \"", "the pending key has a loc entry")


class _StateModifierEngine(_Engine):
    """A state's modifiers as {name: multiplier}, for the Wealth Concentration state modifiers."""

    def __init__(self, **kwargs):
        super().__init__(fixtures={}, **kwargs)
        self.effects.update(_raw_blocks([INH_EFFECTS]))
        self.values.update(_raw_blocks([INH_VALUES]))
        self.modifiers = {}

    def _test(self, key, op, arg):
        if key == "has_modifier":
            return arg in self.modifiers
        return super()._test(key, op, arg)

    def run(self, items):
        rest = []
        for item in items:
            key, _, arg = item
            if key == "remove_modifier":
                self._flush(rest)
                rest = []
                assert arg in self.modifiers, f"remove of absent modifier {arg}"
                del self.modifiers[arg]
            elif key == "add_modifier":
                self._flush(rest)
                rest = []
                name = _find(arg, "name")
                assert name not in self.modifiers, f"{name} added twice"
                self.modifiers[name] = self.value(_find(arg, "multiplier"))
            else:
                rest.append(item)
        self._flush(rest)

    def _flush(self, items):
        if items:
            super().run(items)


class TestWealthStateModifiers(unittest.TestCase):
    """Spec 4.2's split (phase 2): two country modifiers from the national figure, three state
    modifiers from each state's own score, each with one refresh site."""

    def refresh(self, wc, agr, before=()):
        eng = _StateModifierEngine()
        eng.vars.update(te_dg_wc=float(wc), te_dg_agr_share=float(agr))
        eng.modifiers.update({name: 0.5 for name in before})
        eng.call("te_inh_refresh_wc_state_effects")
        return eng

    def test_the_state_modifiers_follow_the_states_own_score(self):
        cases = (
            # score, agrarian share -> concentrated, dispersed, land hunger
            (80, 0.5, 0.6, None, 0.3),
            (100, 1.0, 1.0, None, 1.0),
            (100, 0.0, 1.0, None, None),   # a city: no land hunger
            (50, 0.8, None, None, None),
            (50.4, 0.8, None, None, None),  # under 0.01: not applied
            (20, 0.8, None, 0.6, None),
            (0, 0.3, None, 1.0, None),
        )
        for wc, agr, high, low, hunger in cases:
            eng = self.refresh(wc, agr, before=STATE_WC_MODIFIERS)
            got = tuple(eng.modifiers.get(n) for n in STATE_WC_MODIFIERS)
            for g, want in zip(got, (high, low, hunger)):
                if want is None:
                    self.assertIsNone(g, (wc, agr))
                else:
                    self.assertAlmostEqual(g, want, msg=(wc, agr))
            for name in STATE_WC_MULTS:
                self.assertIn(name, eng.vars, "the multipliers stay set, even at 0")

    def test_a_state_with_no_score_yet_loses_stale_modifiers(self):
        eng = _StateModifierEngine()
        eng.modifiers.update({name: 0.5 for name in STATE_WC_MODIFIERS})
        eng.call("te_inh_refresh_wc_state_effects")
        self.assertEqual(eng.modifiers, {})

    def test_the_refresh_reads_this_years_score_whatever_the_rule(self):
        body = _block(_text(EFFECTS), "te_demog_state_yearly")
        refresh = body.index("te_inh_refresh_wc_state_effects = yes")
        self.assertLess(body.index("te_demog_wc_state_yearly = yes"), refresh)
        self.assertLess(refresh, body.index("te_demog_state_census = yes"))
        self.assertNotIn("te_demog_cohorts_run", body, "owner's ruling: every rule setting")

    def test_one_refresh_site_per_modifier(self):
        files = [p for d in ("common", "events") for p in (ROOT / d).rglob("*.txt")]
        adds = {}
        calls = []
        for path in files:
            for name, body in _raw_blocks([path]).items():
                for m in re.finditer(r"add_modifier = \{\s*name = (inh_\w+)", body):
                    adds.setdefault(m.group(1), set()).add(name)
                calls += [name] * body.count("te_inh_refresh_wc_state_effects = yes")
        for name in STATE_WC_MODIFIERS:
            self.assertEqual(adds.get(name), {"te_inh_refresh_wc_state_effects"}, name)
        for name in ("inh_great_fortunes", "inh_dispersed_wealth"):
            self.assertEqual(adds.get(name), {"te_inh_apply_concentration_modifiers"}, name)
        self.assertEqual(sorted(calls), ["inheritance_events.8", "te_demog_state_yearly"])

    def test_the_modifiers_split_by_scope(self):
        mods = _raw_blocks([INH_MODIFIERS])
        for name, prefixes in (("inh_great_fortunes", ("country_",)), ("inh_dispersed_wealth", ("country_",)),
                               *((n, ("state_",)) for n in STATE_WC_MODIFIERS)):
            fields = re.findall(r"^\s*(\w+) = ", mods[name], re.M)
            fields = [f for f in fields if f != "icon"]
            self.assertTrue(fields, name)
            for f in fields:
                self.assertTrue(f.startswith(prefixes), f"{name}: {f}")

    def test_the_multipliers_are_never_removed(self):
        """modifier_multiplier_var_audit's rule: a modifier's multiplier is re-read after it is applied."""
        for path in [p for d in ("common", "events") for p in (ROOT / d).rglob("*.txt")]:
            text = _text(path)
            for name in STATE_WC_MULTS:
                self.assertNotRegex(text, rf"remove_variable = (\{{ name = )?{name}\b", path.name)

    def test_game_start_refreshes_every_state_from_its_own_scope(self):
        events = _raw_blocks([INH_EVENTS])
        start = events["inheritance_events.1"]
        self.assertLess(start.index("te_inh_game_start = yes"), start.index("id = inheritance_events.8"))
        self.assertIn("every_scope_state", start)
        state = events["inheritance_events.8"]
        self.assertIn("type = state_event", state)
        self.assertIn("hidden = yes", state)
        self.assertIn("te_inh_refresh_wc_state_effects = yes", state)


EXTRA_LAWS = ROOT / "common" / "laws" / "extra_laws.txt"
DEMOG_GUI = ROOT / "gui" / "te_demographics_widgets.gui"


class _LawEngine(_Engine):
    """A country holding `laws`, for the values that read has_law."""

    def __init__(self, laws, **kwargs):
        super().__init__(**kwargs)
        self.values.update(_raw_blocks([INH_VALUES]))
        self.laws = set(laws)

    def _test(self, key, op, arg):
        if key == "has_law":
            assert arg.startswith("law_type:"), arg
            return arg[9:] in self.laws
        return super()._test(key, op, arg)


class TestInheritanceBalance(unittest.TestCase):
    """The 2026-10-09 balance pass (owner's table): the economic laws term, the re-centred
    ownership term, the amendments, the laws and The Great Estates for Sale."""

    def test_the_economic_laws_term(self):
        cases = (
            ((), 0),
            (("law_traditionalism", "law_guilds_chartered_monopolies"), 5),     # the 1836 baseline
            (("law_laissez_faire", "law_freedom_of_contract"), 15),             # the Gilded Age
            (("law_extraction_economy", "law_guilds_chartered_monopolies"), 10),
            (("law_interventionism", "law_trust_busting"), -10),
            (("law_command_economy", "law_command_cooperative_economy"), 0),    # counted in ownership
            (("law_interventionism", "law_regulated_utilities"), -10),
        )
        for laws, want in cases:
            eng = _LawEngine(laws, fixtures={})
            self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_wc_econ_term")), want, laws)

    def test_the_economic_laws_term_is_wired_like_the_tax_term(self):
        self.assertIn("add = owner.te_demog_wc_econ_term", _block(_text(VALUES), "te_demog_wc_target"))
        self.assertIn("set_variable = { name = te_dg_wc_t_econ value = te_demog_wc_econ_term }",
                      _block(_text(WEALTH_EFFECTS), "te_demog_wc_national"))
        self.assertIn("ScriptValue('te_demog_wc_econ_term')", _text(DEMOG_GUI))

    def test_the_shown_target_follows_an_economic_law_at_once(self):
        eng = _CountryEngine(fixtures={"te_inh_law_amendment_target": 75.0, "te_demog_wc_tax_term": -5.0,
                                       "te_demog_wc_econ_term": 15.0})
        eng.values.update(_raw_blocks([INH_VALUES]))
        eng.vars.update(te_dg_wc_target=60.0, te_dg_wc_t_law=25.0, te_dg_wc_t_tax=-5.0, te_dg_wc_t_econ=5.0,
                        te_inh_concentration=33.0)
        eng.run(_parse_script("set_variable = { name = shown value = te_inh_concentration_target }"))
        self.assertAlmostEqual(eng.vars["shown"], 70.0, msg="Laissez-Faire enacted since the refresh: +10")

    def test_the_ownership_term_is_centred_on_1836s_measured_share(self):
        body = _block(_text(VALUES), "te_demog_wc_ownership_term")
        self.assertIn("subtract = 0.65", body)

    def test_the_amendments_move_the_law_target(self):
        body = _block(_text(INH_VALUES), "te_inh_law_amendment_target")
        shifts = dict(re.findall(r"amendment_type:(amendment_\w+)\s*\}\s*\}\s*add = (-?\d+)", body))
        self.assertEqual(shifts, {"amendment_estate_duties": "-30", "amendment_birthright_endowment": "-20",
                                  "amendment_perpetual_trusts": "30", "amendment_undivided_farm_succession": "10"})
        endowment = _raw_blocks([ROOT / "common" / "amendments" / "extra_amendments.txt"])["amendment_birthright_endowment"]
        self.assertIn("country_bureaucracy_investment_cost_factor_mult = 0.05", endowment, "the stakes' cost")

    def test_no_inheritance_law_repeats_what_the_score_carries(self):
        """Radicals, qualifications and education access come from the state's score
        (inh_concentrated_property); a law carrying them too counts them twice."""
        laws = {name: body for name, body in _raw_blocks([EXTRA_LAWS]).items()
                if "group = lawgroup_inheritance" in body}
        self.assertEqual(len(laws), 6)
        for name, body in laws.items():
            modifier = body[body.index("modifier = {"):]
            for field in ("state_radicals_from_political_movements_mult", "state_pop_qualifications_mult",
                          "state_education_access_add"):
                self.assertNotIn(field, modifier, name)
            self.assertRegex(modifier, r"modifier = \{\s*\w", f"{name}: every law has an effect of its own")

    def test_the_great_estates_for_sale_trade_money_for_levelling(self):
        """Buying the estates for smallholders costs money and levels more; letting the market take
        them earns the duty and levels little (playtest: both used to level by 5)."""
        event = _raw_blocks([INH_EVENTS])["inheritance_events.5"]
        shifts = dict(re.findall(r"name = inheritance_events\.5\.(\w)\s.*?AMOUNT = (-?\d+)", event, re.S))
        self.assertEqual(shifts, {"a": "-10", "b": "-2", "c": "3"})


HISTORY_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_history_effects.txt"
BOM = b"\xef\xbb\xbf"


def _walk(items):
    """Every (key, operator, value) in a parsed script, depth first."""
    for item in items:
        yield item
        if isinstance(item[2], list):
            yield from _walk(item[2])


class TestHistory(unittest.TestCase):
    """Task 12: the yearly history store (te_demog_history_record), modelled on the Cultural
    Hegemony annual store. The interpreter has no containers, so these read the script."""

    @classmethod
    def setUpClass(cls):
        cls.text = _text(HISTORY_EFFECTS) if HISTORY_EFFECTS.exists() else ""

    def block(self, name):
        return _block(self.text, name)

    def test_file_has_one_bom_and_tabs(self):
        raw = HISTORY_EFFECTS.read_bytes()
        self.assertTrue(raw.startswith(BOM))
        self.assertFalse(raw[len(BOM):].startswith(BOM), "a doubled BOM drops the whole file")
        self.assertNotRegex(raw.decode("utf-8-sig"), r"(?m)^ +\S")

    def test_the_census_calls_the_record_for_tracked_countries_only(self):
        body = _block(_text(EFFECTS), "te_demog_country_census")
        calls = [i for i in _walk(_parse_script(body)) if i[0] == "te_demog_history_record"]
        self.assertEqual(len(calls), 1)
        gates = [v for k, _, v in _walk(_parse_script(body))
                 if k == "if" and any(i[0] == "te_demog_history_record" for i in v)]
        self.assertEqual(len(gates), 1)
        self.assertIn(("te_history_country_is_tracked", "=", "yes"), _find(gates[0], "limit"))
        # at the end of the effect, once the figures are written (inside the seeded branch)
        self.assertLess(body.index("te_demog_project = yes"), body.index("te_demog_history_record = yes"))
        self.assertGreater(body.index("te_demog_history_record = yes"), body.rindex("te_demog_set_trend = yes"))

    def census(self, tracked, states):
        stub = {"te_demog_history_record": "set_variable = { name = hist_median value = var:te_dg_median }"}
        eng = _CountryEngine(states=states, fixtures={"year": 1900.0, "te_demog_female_work_share": 0.25},
                             triggers={"is_ai": True, "te_demog_cohorts_run": True,
                                       "te_history_country_is_tracked": tracked}, effects=stub)
        eng.call("te_demog_country_census")
        return eng.vars

    def test_the_record_runs_after_the_figures_are_written(self):
        states = [TestCountry.state(4_000_000, 1_600_000, 22, 0.55, rank=1),
                  TestCountry.state(1_500_000, 300_000, 14, 0.3, rank=2)]
        v = self.census(True, [dict(s) for s in states])
        self.assertGreater(v["hist_median"], 15)
        self.assertEqual(v["hist_median"], v["te_dg_median"])
        self.assertNotIn("hist_median", self.census(False, [dict(s) for s in states]))
        pending = [{"te_dg_people": 5e5, "state_population": 5e5}]   # no state seeded: no census, no sample
        self.assertNotIn("hist_median", self.census(True, pending))

    def test_one_sample_a_year(self):
        """The census runs twice in 1836 (game start, 31 December): the year is checked before a
        container is created, and set only once the sample is stored."""
        body = self.block("te_demog_history_record")
        self.assertLess(body.index("te_dg_hist_year"), body.index("create_container"))
        guard = body[:body.index("create_container")]
        self.assertIn("var:te_dg_hist_year = te_demog_year", guard)
        self.assertIn("NOT = { has_variable = te_dg_hist_year }", guard)

    def test_a_revolutions_winner_starts_a_list_in_the_year_it_wins(self):
        """The winner inherits te_dg_hist_year but not the list (best practices, container rule 4):
        a country with no list creates a container whatever its year says, and the refill reads the
        list only once it exists. The interpreter has no containers or lists, so this pins the text."""
        body = self.block("te_demog_history_record")
        guard = _find(_find(_parse_script(body), "hidden_effect"), "if")
        either = _find(_find(guard, "limit"), "OR")
        self.assertIn(("NOT", "=", [("has_variable_list", "=", "te_dg_hist")]), either)
        self.assertEqual(len(either), 3)
        refills = [v for k, _, v in _walk(_parse_script(body))
                   if k == "if" and any(i[0] == "every_in_list" for i in v)]
        self.assertEqual(len(refills), 1)
        self.assertEqual(_find(refills[0], "limit"), [("has_variable_list", "=", "te_dg_hist")])
        self.assertEqual(body.count("every_in_list"), 1)
        self.assertEqual(body.count("create_container"), 1)
        self.assertRegex(body, r"set_variable = \{ name = te_dg_hist_year value = te_demog_year \}")
        self.assertLess(body.index("add_to_variable_list"),
                        body.index("set_variable = { name = te_dg_hist_year value = te_demog_year }"))
        self.assertIn("limit = { exists = scope:te_dg_hist_new }", body)

    def test_the_sample_is_a_country_owned_container_keyed_by_year(self):
        body = self.block("te_demog_history_record")
        self.assertIn("parent = scope:te_dg_hist_owner", body)
        self.assertIn("save_scope_as = te_dg_hist_owner", body)
        self.assertRegex(body, r"set_variable = \{ name = te_hist_i value = te_demog_year \}")
        self.assertRegex(body, r"add_to_variable_list = \{ name = te_dg_hist target = scope:te_dg_hist_new \}")
        self.assertTrue(body.lstrip().startswith("hidden_effect"), "hidden: a store, not a tooltip")

    def test_this_years_container_is_refilled_every_run(self):
        """The 31 December run overwrites the game-start sample's values. The game-start sample may
        lack the Gini and Wealth Concentration: te_demog_wc_national runs on the yearly pulse and from
        te_inh_game_start, and the two game-start events run in either order."""
        body = self.block("te_demog_history_record")
        self.assertRegex(body, r"every_in_list = \{\s+variable = te_dg_hist\s+limit = \{ var:te_hist_i = te_demog_year \}")
        self.assertGreater(body.index("every_in_list"), body.index("te_dg_hist_year value"))
        copies = dict(re.findall(r"te_demog_history_copy = \{ FROM = (\w+) TO = (\w+) \}", body))
        self.assertEqual(copies, {"te_dg_median": "te_dg_h_median", "te_dg_tfr": "te_dg_h_tfr",
                                  "te_dg_e0": "te_dg_h_e0", "te_dg_gini": "te_dg_h_gini",
                                  "te_inh_concentration": "te_dg_h_wc"})

    def test_each_read_is_guarded_by_has_variable(self):
        body = self.block("te_demog_history_copy")
        self.assertRegex(body, r"limit = \{ scope:te_dg_hist_owner = \{ has_variable = \$FROM\$ \} \}")
        self.assertIn("value = scope:te_dg_hist_owner.var:$FROM$", body)
        self.assertIn("name = $TO$", body)

    def test_the_store_holds_100_and_each_eviction_sorts_again(self):
        prune = self.block("te_demog_history_prune")
        self.assertRegex(prune, r"any_in_list = \{ variable = te_dg_hist count >= 101 has_tag = te_dg_hist_sample \}")
        self.assertIn("cap 100", prune)
        self.assertIn("order_by = te_history_sample_order", prune)
        self.assertLess(prune.index("remove_list_variable"), prune.index("destroy_container = yes"))
        self.assertLess(prune.index("destroy_container = yes"), prune.index("te_demog_history_sort = yes"))
        self.assertIn("fills the hole", re.sub(r"\n#\s*", " ", self.text))   # the eviction comment (CH's)
        self.assertIn("te_demog_history_prune = yes", self.block("te_demog_history_record"))

    def test_the_sort_builds_the_copy_before_clearing_the_list(self):
        sort = self.block("te_demog_history_sort")
        self.assertEqual(sort.count("max = 100"), 2)
        self.assertRegex(sort, r"any_in_list = \{ variable = te_dg_hist_tmp count >= 100 has_tag = te_dg_hist_sample \}")
        self.assertEqual(sort.count("check_range_bounds = no"), 2)
        self.assertLess(sort.index("add_to_variable_list = { name = te_dg_hist_tmp"),
                        sort.index("clear_variable_list = te_dg_hist\n"))
        self.assertEqual(sort.count("order_by = te_history_sample_order"), 2)
        self.assertGreater(sort.rindex("clear_variable_list = te_dg_hist_tmp"), sort.rindex("add_to_variable_list"))

    def test_the_order_value_is_negated_so_the_oldest_comes_first(self):
        order = _block(_text(ROOT / "common" / "script_values" / "te_history_values.txt"), "te_history_sample_order")
        self.assertRegex(order, r"subtract = var:te_hist_i")

    def test_no_name_is_shared_with_the_other_stores(self):
        """The Cultural Hegemony and monthly stores run in the same pulses: their lists, scratch
        lists, saved scopes and tags must stay theirs."""
        for stale in (r"variable = te_hist\b", r"te_hist_tmp", r"te_hist_sorter", r"te_hist_evicted", r"te_hist_moved",
                      r"te_hist_sample\b", r"ch_model", r">= 241", r">= 240", r"max = 240"):
            self.assertNotRegex(self.text, stale)


# -- the console (te_debug_demog.1, Task 15) -------------------------------------------------------

CONSOLE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"


def _console_blocks():
    """te_debug_demog_effects.txt's effects as _raw_blocks gives them, each debug_log string swapped
    for a token (_parse_script splits on spaces and `=`): (blocks, {token: the string})."""
    strings = {}

    def token(m):
        key = f"LOG{len(strings)}"
        strings[key] = m.group(1)
        return f"debug_log = {key}"

    text = re.sub(r"#[^\n]*", "", re.sub(r'debug_log = "([^"]*)"', token, _text(CONSOLE_EFFECTS)))
    blocks = {}
    for m in re.finditer(r"^([\w.]+) = \{", text, re.M):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        blocks[m.group(1)] = text[m.end():i - 1]
    return blocks, strings


class _ConsoleEngine(_Engine):
    """_Engine plus the console's effects. A debug_log is a no-op that records (its string, the
    variables as they stood); the generated ring lines are one debug_log each, RING_BEFORE and
    RING_AFTER."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        blocks, self.strings = _console_blocks()
        self.effects.update(blocks)
        self.effects["te_demog_debug_log_ring_before"] = "debug_log = RING_BEFORE"
        self.effects["te_demog_debug_log_ring_after"] = "debug_log = RING_AFTER"
        self.logs = []

    def run(self, items):
        segment = []
        for item in items:
            if item[0] != "debug_log":
                segment.append(item)
                continue
            super().run(segment)
            segment = []
            self.logs.append((self.strings.get(item[2], item[2]), dict(self.vars)))
        super().run(segment)


class TestConsole(unittest.TestCase):
    def test_step_is_its_two_halves(self):
        """Option a logs between te_demog_step_begin and te_demog_step_run, so the step must be exactly
        the two, with the rates and flows in the first half and none of them in the second."""
        text = _text(EFFECTS)
        self.assertEqual(_block(text, "te_demog_step").split(),
                         ["te_demog_step_begin", "=", "yes", "te_demog_step_run", "=", "yes"])
        begin = _block(text, "te_demog_step_begin")
        self.assertLess(begin.index("te_demog_prepare = yes"), begin.index("te_demog_flows = yes"))
        run = _block(text, "te_demog_step_run")
        for name in ("te_demog_prepare", "te_demog_flows"):
            self.assertNotIn(name, run)
        self.assertIn("te_demog_sweep = yes", run)

    def test_the_census_log_hooks_are_gated(self):
        text = _text(EFFECTS)
        for caller, line in (("te_demog_state_yearly", "te_debug_demog_pulse_line"),
                             ("te_demog_country_census", "te_debug_demog_census_line")):
            self.assertRegex(_block(text, caller),
                             rf"if = \{{\s*limit = \{{ te_demog_census_log_on = yes \}}\s*{line} = yes\s*\}}", caller)
        self.assertIn("has_global_variable = te_demog_census_log", _block(_text(TRIGGERS), "te_demog_census_log_on"))

    def test_only_the_console_sets_the_census_log(self):
        setters = [p for p in [*ROOT.glob("common/**/*.txt"), *ROOT.glob("events/*.txt")]
                   if "set_global_variable = te_demog_census_log" in _text(p)]
        self.assertEqual([p.name for p in setters], ["te_debug_demog_events.txt"])

    def test_every_debug_copy_is_removed(self):
        """A line renders when it runs; the te_dg_dbg_ variables only carry its numbers and must not
        stay in the save."""
        blocks, _ = _console_blocks()
        for name, body in blocks.items():
            for var in set(re.findall(r"set_variable = \{ name = (te_dg_dbg_\w+)", body)):
                self.assertIn(f"remove_variable = {var}", body, f"{name}: {var}")

    def test_the_benchmark_leaves_a_census_behind(self):
        """Its timed passes step every census a second time in one year; after the last BENCH line it
        seeds every state with a census again, and nothing follows the seed loop."""
        body = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_benchmark")
        last_pass = body.index("TE_DEMOG_BENCH pass=3 end")
        reseed = body.index('debug_log = "TE_DEMOG_BENCH reseed"')
        self.assertGreater(reseed, last_pass)
        tail = body[reseed + len('debug_log = "TE_DEMOG_BENCH reseed"'):]
        self.assertRegex(tail, r"^\s*every_state = \{\s*limit = \{ te_demog_has_census = yes \}\s*(#[^\n]*\s*)*"
                               r"te_demog_seed_off_pulse = yes\s*\}\s*$")
        self.assertEqual(body.count("TE_DEMOG_BENCH"), 8, "start, three begin/end pairs, reseed")

    def test_the_census_line_waits_for_a_million_people(self):
        body = _console_blocks()[0]["te_debug_demog_census_line"]
        self.assertIn("local_var:te_dg_c_people >= 1000000", body)
        self.assertIn("name = te_dg_c_people", _block(_text(EFFECTS), "te_demog_country_census"))

    def test_option_m_logs_the_shock_terms_click_only(self):
        console = _text(DEBUG_EVENTS)
        call = "te_debug_demog_shock_lines = yes"
        self.assertEqual(console.count(call), 1)
        guard = console[console.rindex("limit = { has_variable = te_dg_dbg_click }", 0, console.index(call)):
                        console.index(call)]
        self.assertIn("remove_variable = te_dg_dbg_click", guard)
        body = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_shock_lines")
        for read in ("modifier:state_mortality_mult", "modifier:state_birth_rate_mult", "value = devastation",
                     "value = turmoil", "value = state_region.pollution_amount", "debug_log_scopes = yes"):
            self.assertIn(read, body)
        for name in ("te_dg_dbg_read_d", "te_dg_dbg_read_b", "te_dg_dbg_dev", "te_dg_dbg_turmoil", "te_dg_dbg_poll"):
            self.assertIn(f"remove_variable = {name}", body)

    def test_option_n_logs_the_rates_click_only(self):
        console = _text(DEBUG_EVENTS)
        call = "te_debug_demog_rate_lines = yes"
        self.assertEqual(console.count(call), 1)
        guard = console[console.rindex("limit = { has_variable = te_dg_dbg_click }", 0, console.index(call)):
                        console.index(call)]
        self.assertIn("remove_variable = te_dg_dbg_click", guard)
        body = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_rate_lines")
        copies = set(re.findall(r"(?:set_variable = \{ name = |TO = )(te_dg_dbg_\w+)", body))
        self.assertTrue(copies)
        for var in copies:
            self.assertIn(f"remove_variable = {var}", body, var)
        line = re.search(r'debug_log = "(TE_DEMOG_RATES:[^"]*)"', body).group(1)
        read = re.findall(r"Var\('(\w+)'\)", line)
        self.assertTrue(read)
        self.assertEqual([v for v in read if not v.startswith("te_dg_dbg_")], [], "raw census variables in the line")


FAST_EVENTS = ROOT / "events" / "te_demog_events.txt"
DEBUG_EVENTS = ROOT / "events" / "te_debug_demog_events.txt"
DEBUG_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_debug_demog_modifiers.txt"


class TestFastMode(unittest.TestCase):
    """Fast mode (te_demog_fast_effects.txt; te_debug_demog.1 options h-k, console only): the census on its own
    clock, a step every N months for every state from the global monthly pulse, and the engine's births, deaths,
    research and construction at K = 12 / N times."""

    CLOCK = {"global_var:te_demog_clock": 1900.0, "global_var:te_demog_months_per_step": 3.0,
             "global_var:te_demog_window_months": 3.0}

    def _eng(self, clock_on, fixtures=None, effects=None, triggers=None):
        return _Engine({"year": 1837.0, **(self.CLOCK if clock_on else {}), **(fixtures or {})},
                       triggers={"te_demog_clock_on": clock_on, "te_demog_cohorts_run": True, **(triggers or {})},
                       effects=effects)

    def test_the_census_year_is_the_clocks_while_it_runs(self):
        self.assertEqual(self._eng(False).value("te_demog_year"), 1837.0)
        self.assertEqual(self._eng(True).value("te_demog_year"), 1900.0)

    def test_a_step_covers_a_year_or_the_clocks_window(self):
        self.assertEqual(self._eng(False).value("te_demog_step_months"), 12.0)
        self.assertEqual(self._eng(True, {"global_var:te_demog_window_months": 5.0}).value("te_demog_step_months"), 5.0)

    def test_k_is_twelve_months_over_the_months_a_step(self):
        self.assertEqual(self._eng(False).value("te_demog_fast_k"), 1.0)
        for months, k in ((3, 4.0), (2, 6.0), (1, 12.0), (12, 1.0)):
            eng = self._eng(True, {"global_var:te_demog_months_per_step": float(months)})
            self.assertEqual(eng.value("te_demog_fast_k"), k, months)
            self.assertEqual(eng.value("te_demog_fast_k_minus_1"), k - 1, months)

    def _refresh(self, eng, eb, eb0, ed, ed0):
        eng.locals.update(te_dg_w_eb=eb, te_dg_w_eb0=eb0, te_dg_w_ed=ed, te_dg_w_ed0=ed0)
        eng.call("te_demog_fast_refresh_rates")

    def test_the_rate_term_is_k_minus_1_times_the_states_own_average(self):
        """A flat +(K - 1) would dilute the state's other terms, which the engine adds into the same (1 + total):
        the term scales with the state's average multiplier instead, so its births and deaths run K times."""
        eng = self._eng(True)   # K = 4
        self._refresh(eng, eb=105.0, eb0=100.0, ed=96.0, ed0=100.0)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fb"], 3 * 1.05)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fd"], 3 * 0.96)
        self.assertAlmostEqual(eng.modifiers["te_demog_fast_births"], 3 * 1.05)
        self.assertAlmostEqual(eng.modifiers["te_demog_fast_deaths"], 3 * 0.96)
        # births at the state's (1 + total) with the term: 1.05 + 3.15 = 4.2 = 4 x 1.05
        self.assertAlmostEqual(1.05 + eng.vars["te_dg_fast_fb"], 4 * 1.05)

    def test_the_term_is_a_fixed_point_once_applied(self):
        """The next walk's multipliers hold the term already applied, which comes off before it is scaled."""
        eng = self._eng(True)
        self._refresh(eng, eb=105.0, eb0=100.0, ed=96.0, ed0=100.0)
        fb, fd = eng.vars["te_dg_fast_fb"], eng.vars["te_dg_fast_fd"]
        self._refresh(eng, eb=100.0 * (1.05 + fb), eb0=100.0, ed=100.0 * (0.96 + fd), ed0=100.0)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fb"], fb)
        self.assertAlmostEqual(eng.vars["te_dg_fast_fd"], fd)

    def test_a_state_with_nobody_gets_no_term(self):
        eng = self._eng(True)
        self._refresh(eng, eb=0.0, eb0=0.0, ed=0.0, ed0=0.0)
        self.assertEqual(eng.vars["te_dg_fast_fb"], 0.0)
        self.assertEqual(eng.modifiers["te_demog_fast_births"], 0.0)

    def test_normal_speed_takes_the_modifiers_and_their_terms_off(self):
        eng = self._eng(True)
        self._refresh(eng, eb=105.0, eb0=100.0, ed=96.0, ed0=100.0)
        eng.fixtures["global_var:te_demog_months_per_step"] = 12.0   # K = 1
        self._refresh(eng, eb=420.0, eb0=100.0, ed=384.0, ed0=100.0)
        self.assertEqual(eng.modifiers, {})
        self.assertNotIn("te_dg_fast_fb", eng.vars)
        self.assertNotIn("te_dg_fast_fd", eng.vars)

    STUBS = {"te_demog_walks": "set_variable = { name = walked value = 1 }",
             "te_inh_refresh_rural_effects": "set_variable = { name = rural value = 1 }",
             "te_demog_wc_state_yearly": "set_variable = { name = wc value = 1 }",
             "te_inh_refresh_wc_state_effects": "set_variable = { name = wc_mods value = 1 }",
             "te_demog_fast_refresh_rates": "set_variable = { name = rates value = 1 }",
             "te_demog_rates_refresh": "set_variable = { name = census_rates value = 1 }",
             "te_demog_seed": "set_variable = { name = did value = 1 }",
             "te_demog_step": "set_variable = { name = did value = 2 }"}

    def test_under_the_clock_the_yearly_pulse_keeps_inheritance_and_wealth_only(self):
        eng = self._eng(True, {"state_population": 1000.0}, effects=self.STUBS)
        # a state with a census was walked at a clock step (te_dg_walk_pop)
        eng.vars.update(te_dg_year=1899.0, te_dg_raw=900.0, te_dg_pop_last=1000.0, te_dg_walk_pop=1000.0)
        eng.call("te_demog_state_yearly")
        self.assertEqual({k: eng.vars.get(k) for k in ("walked", "rural", "wc", "wc_mods", "did")},
                         {"walked": None, "rural": 1.0, "wc": 1.0, "wc_mods": 1.0, "did": None})

    def test_a_clock_step_walks_steps_and_refreshes_the_rates(self):
        cases = [((1899.0, 1000.0), 2),   # a step on: the census steps
                 ((1898.0, 1000.0), 1),   # a step missed (no owner at it): seed again
                 ((1899.0, 1300.0), 1)]   # a merge or split: seed again
        for (census, pop), want in cases:
            eng = self._eng(True, {"state_population": pop}, effects=self.STUBS)
            eng.vars.update(te_dg_year=census, te_dg_raw=900.0, te_dg_pop_last=1000.0)
            eng.call("te_demog_state_clock_step")
            self.assertEqual((eng.vars.get("walked"), eng.vars.get("did"), eng.vars.get("rates")), (1.0, want, 1.0),
                             (census, pop))
            self.assertEqual(eng.vars.get("census_rates"), 1.0, "the census's terms are refreshed at each clock step")
            self.assertIsNone(eng.vars.get("wc"), "Wealth Concentration stays on the yearly pulse")

    def test_the_tick_steps_every_state_before_the_census_a_day_later(self):
        """The clock advances before the step events, which fire at once; the census events wait a day, so every
        state has stepped when a country sums them (the census line's lag counts any that had not)."""
        body = re.sub(r"#[^\n]*", "", _block(_text(FAST_EFFECTS), "te_demog_clock_tick"))
        advance = body.index("change_global_variable = { name = te_demog_clock add = 1 }")
        steps = body.index("trigger_event = { id = te_demog_events.2 }")
        census = body.index("trigger_event = { id = te_demog_events.3 days = 1 }")
        self.assertLess(advance, steps)
        self.assertLess(steps, census)
        self.assertIn("set_global_variable = { name = te_demog_window_months value = global_var:te_demog_clock_month }",
                      body[:advance])
        events = _text(FAST_EVENTS)
        self.assertIn("te_demog_state_clock_step = yes", _block(events, "te_demog_events.2"))
        self.assertIn("type = state_event", _block(events, "te_demog_events.2"))
        self.assertIn("te_demog_country_clock_census = yes", _block(events, "te_demog_events.3"))
        hook = _block(_text(DEMOG_ON_ACTIONS), "te_demog_clock_on_action")
        self.assertIn("te_demog_clock_on = yes", hook)
        self.assertIn("te_demog_clock_tick = yes", hook)

    def test_the_31_december_census_waits_for_no_clock(self):
        body = _block(_text(EFFECTS), "te_demog_country_yearly")
        gate = body[body.index("limit = {", body.index("te_demog_wc_national = yes")):body.index("te_demog_country_census = yes")]
        self.assertIn("NOT = { te_demog_clock_on = yes }", gate)

    def test_the_first_switch_re_seeds_and_every_switch_is_click_only(self):
        body = _block(_text(FAST_EFFECTS), "te_demog_fast_set")
        first = body[body.index("NOT = { te_demog_clock_on = yes }"):body.index("set_global_variable = { name = te_demog_months_per_step")]
        self.assertIn("set_variable = { name = te_dg_reseed value = 1 }", first)
        console = _text(DEBUG_EVENTS)
        for months in ("3", "2", "1", "12"):
            call = f"te_demog_fast_set = {{ MONTHS = {months} }}"
            self.assertEqual(console.count(call), 1, months)
            guard = console[console.rindex("limit = { has_variable = te_dg_dbg_click }", 0, console.index(call)):
                            console.index(call)]
            self.assertIn("remove_variable = te_dg_dbg_click", guard, months)

    def test_the_fast_modifiers_are_plus_one_fields(self):
        mods = _raw_blocks([DEBUG_MODIFIERS])
        for name, fields in (("te_demog_fast_births", {"state_birth_rate_mult"}),
                             ("te_demog_fast_deaths", {"state_mortality_mult"}),
                             ("te_demog_fast_speed", {"country_tech_research_speed_mult", "country_tech_spread_mult",
                                                      "state_construction_mult"})):
            got = dict(re.findall(r"^\s*(\w+) = (\S+)", mods[name], re.M))
            got.pop("icon")
            self.assertEqual(got, dict.fromkeys(fields, "1"), name)


TYPES_FILE = ROOT / "common" / "modifier_type_definitions" / "demographics_modifier_types.txt"
MODIFIERS_LOC = ROOT / "localization" / "english" / "te_modifiers_l_english.yml"
ENGINE_MODIFIERS = ROOT / "docs" / "engine" / "modifiers_summary.txt"


class TestModifierTypes(unittest.TestCase):
    """Stage 1 of the modifier-types design: every mortality input is a registered, named type."""

    def test_every_type_is_registered_script_only(self):
        text = _text(TYPES_FILE)
        for name in P.DEMOG_MORTALITY_TYPES:
            body = _block(text, name)
            self.assertIn("script_only = yes", body, name)
            self.assertRegex(body, r"decimals = \d", name)

    def test_every_type_has_a_name_and_a_description(self):
        loc = _text(MODIFIERS_LOC)
        for name in P.DEMOG_MORTALITY_TYPES:
            self.assertRegex(loc, rf"(?m)^ {name}:0 \"", name)
            self.assertRegex(loc, rf"(?m)^ {name}_desc:0 \"", name)

    def test_no_type_is_an_engine_modifier(self):
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        self.assertIn("state_mortality_mult", engine)   # the list is the one this reads
        for name in P.DEMOG_MORTALITY_TYPES:
            self.assertNotIn(name, engine, name)

    def test_fertility_types_are_registered_named_and_new(self):
        text, loc = _text(TYPES_FILE), _text(MODIFIERS_LOC)
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        for name in P.DEMOG_FERTILITY_TYPES:
            self.assertTrue(name.startswith("state_"), name)
            body = _block(text, name)
            self.assertIn("script_only = yes", body, name)
            self.assertRegex(body, r"decimals = \d", name)
            self.assertRegex(loc, rf"(?m)^ {name}:0 \"", name)
            self.assertRegex(loc, rf"(?m)^ {name}_desc:0 \"", name)
            self.assertNotIn(name, engine, name)

    def test_the_old_country_means_type_is_gone(self):
        # Review Focus 5: the rename leaves no reader, carrier, loc key or param behind
        old = "country_fertility_means_add"
        for sub in ("common", "localization", "scripts", "events", "gui"):
            for path in (ROOT / sub).rglob("*"):
                if path.is_file() and path.suffix in (".txt", ".yml", ".py", ".gui"):
                    self.assertNotIn(old, path.read_text(encoding="utf-8-sig", errors="ignore"), str(path))

    def test_option_l_logs_the_fertility_types(self):
        # the stage-2 in-game check: what each state reads for contraception and fertility control
        values = _text(ROOT / "common" / "script_values" / "te_debug_demog_values.txt")
        self.assertIn(f"value = modifier:{P.CONTRACEPTION_TYPE}", _block(values, "te_debug_demog_mod_contra"))
        self.assertIn(f"value = modifier:{P.MEANS_SHIFT_TYPE}", _block(values, "te_debug_demog_mod_fmeans"))
        self.assertIn("value = te_demog_means", _block(values, "te_debug_demog_means"))
        line = _block(_text(ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"), "te_debug_demog_mods_line")
        for key, sv in (("contra", "te_debug_demog_mod_contra"), ("fmeans", "te_debug_demog_mod_fmeans"),
                        ("means", "te_debug_demog_means")):
            self.assertIn(f" {key}=[THIS.ScriptValue('{sv}')|3]", line)

    def test_seven_state_types(self):
        # one type per term, read in state scope; a tech's or law's line reaches the state because
        # states inherit country modifiers (owner, 2026-10-10)
        self.assertEqual(len(set(P.DEMOG_MORTALITY_TYPES)), 7)
        for name in P.DEMOG_MORTALITY_TYPES:
            self.assertTrue(name.startswith("state_"), name)


class TestCauseMultipliersScript(unittest.TestCase):
    """te_demog_mult_<cause> (generated) against demographics_model.cause_multipliers, with the
    modifier types' reads as fixtures: the caps, the floor and the order of the clamps."""

    CASES = [
        {},
        {P.TREATMENT_TYPE["infection"]: 0.81, P.TREATMENT_TYPE["maternal"]: 0.9, P.TREATMENT_TYPE["chronic"]: 0.59},
        {P.ACCESS_TYPE: 0.6, P.TREATMENT_TYPE["infection"]: 0.81, P.TREATMENT_TYPE["maternal"]: 2.0,
         P.TREATMENT_TYPE["chronic"]: 0.3, "state_chronic_mortality_mult": -0.05},
        {P.ACCESS_TYPE: 1.5, P.TREATMENT_TYPE["infection"]: 0.3},
        {"state_work_mortality_mult": -0.9, "state_external_mortality_mult": -0.1},
        {"state_work_mortality_mult": 0.1, "state_external_mortality_mult": 0.3, "state_chronic_mortality_mult": -0.9},
    ]

    def test_script_matches_the_model(self):
        for mods in self.CASES:
            for sol, lit in ((3, 0.1), (6.5, 0.2), (8, 0.0), (20, 0.5), (40, 1.0)):
                inp = demographics_model.Inputs(sol=sol, literacy=lit, mods=dict(mods))
                want = demographics_model.cause_multipliers(inp)
                fixtures = {f"modifier:{t}": mods.get(t, 0.0) for t in P.DEMOG_MORTALITY_TYPES}
                eng = _Engine(fixtures)
                eng.vars.update(te_dg_sol=float(sol), te_dg_lit=float(lit))
                for cause in ("infection", "work", "external", "chronic"):
                    with self.subTest(mods=mods, sol=sol, cause=cause):
                        got = eng.value(eng._tree(eng.values, f"te_demog_mult_{cause}"))
                        self.assertAlmostEqual(got, want[cause], places=9)
                with self.subTest(mods=mods, sol=sol, cause="maternal"):
                    got = eng.value(eng._tree(eng.values, "te_demog_mult_maternal"))
                    self.assertAlmostEqual(got, want["maternal"] * P.MATERNAL_PER_100K_BIRTHS, places=6)

    def test_crowding_matches_the_model(self):
        # the census reads the multiplier the crowding refresh applied (migration_crowding_mult_applied), the
        # harness the modifier's multiplier in the save: the same yearly figure. Slight (-3.8% attraction), 10x
        # density (-45%), past the cap, and a state the refresh has not reached (no modifier, no variable)
        for mult in (0.378, 4.5, 14.5, None):
            eng = _Engine({f"modifier:{t}": 0.0 for t in P.DEMOG_MORTALITY_TYPES})
            eng.vars.update(te_dg_sol=12.0, te_dg_lit=0.3)
            if mult is not None:
                eng.modifiers["migration_crowding"] = mult
                eng.vars["migration_crowding_mult_applied"] = mult
            crowding = 0.0 if mult is None else P.MIGRATION_CROWDING_PULL_PER_MULT * mult
            want = demographics_model.cause_multipliers(demographics_model.Inputs(sol=12, literacy=0.3,
                                                                                  crowding=crowding))
            with self.subTest(mult=mult):
                got = eng.value(eng._tree(eng.values, "te_demog_mult_infection"))
                self.assertAlmostEqual(got, want["infection"], places=9)

    def test_crowding_needs_both_the_modifier_and_the_stored_multiplier(self):
        # a save from before the stored multiplier: the modifier without the variable, until the state's next yearly
        # refresh (677 of 874 states in the 1949 save), must read no term rather than an unset var:; and a variable
        # outliving its modifier must not count (review I1)
        want = demographics_model.cause_multipliers(demographics_model.Inputs(sol=12, literacy=0.3))["infection"]
        for label, modifier, variable in (("modifier only", True, False), ("variable only", False, True)):
            eng = _Engine({f"modifier:{t}": 0.0 for t in P.DEMOG_MORTALITY_TYPES})
            eng.vars.update(te_dg_sol=12.0, te_dg_lit=0.3)
            if modifier:
                eng.modifiers["migration_crowding"] = 1.5
            if variable:
                eng.vars["migration_crowding_mult_applied"] = 1.5
            with self.subTest(label):
                got = eng.value(eng._tree(eng.values, "te_demog_mult_infection"))
                self.assertAlmostEqual(got, want, places=9)

    def test_crowdings_pull_per_multiplier_is_the_modifiers(self):
        # "infection rises by the share attraction falls" holds only while the two agree: a retuned
        # migration_crowding would otherwise leave the census reading the old figure
        body = _raw_blocks([ROOT / "common" / "static_modifiers" / "extra_modifiers.txt"])["migration_crowding"]
        pull = float(re.search(r"state_migration_pull_mult = (-?[0-9.]+)", body).group(1))
        self.assertAlmostEqual(P.MIGRATION_CROWDING_PULL_PER_MULT, -pull)

    def test_the_crowding_refresh_stores_the_multiplier_it_applies(self):
        refresh = _raw_blocks([ROOT / "common" / "scripted_effects" / "extra_effects.txt"])
        refresh = {"te_update_migration_crowding_modifier": refresh["te_update_migration_crowding_modifier"]}
        eng = _Engine({"migration_crowding_mult": 0.378}, effects=refresh)
        eng.modifiers["migration_crowding"] = 0.2
        eng.vars["migration_crowding_mult_applied"] = 0.2
        eng.call("te_update_migration_crowding_modifier")
        self.assertEqual(eng.modifiers, {"migration_crowding": 0.378})
        self.assertEqual(eng.vars["migration_crowding_mult_applied"], 0.378)
        eng.fixtures["migration_crowding_mult"] = 0.0
        eng.call("te_update_migration_crowding_modifier")
        self.assertEqual(eng.modifiers, {})
        self.assertNotIn("migration_crowding_mult_applied", eng.vars)


class TestMeansScript(unittest.TestCase):
    """te_demog_means (generated) against demographics_model.means, with the fertility types' reads as
    fixtures: the tier's clamp before literacy, the shift after it, the cap and the floor (stage 2's
    Review Focus 1, 3 and 4). In game the one read of state_fertility_means_add carries both the laws'
    lines (mods) and static modifiers such as Family Limitation (means_add)."""

    def test_script_matches_the_model(self):
        for contra in (-1.0, 0.0, 0.2, 0.45, 0.65, 2.0):
            for shift in (-2.0, -0.2, 0.0, 0.1, 1.0):
                for static in (0.0, P.FAMILY_LIMITATION_MEANS):
                    for lit in (0.0, 0.35, 1.0):
                        inp = demographics_model.Inputs(
                            literacy=lit, mods={P.CONTRACEPTION_TYPE: contra, P.MEANS_SHIFT_TYPE: shift},
                            means_add=static)
                        eng = _Engine({f"modifier:{P.CONTRACEPTION_TYPE}": contra,
                                       f"modifier:{P.MEANS_SHIFT_TYPE}": shift + static})
                        eng.vars["te_dg_lit"] = lit
                        with self.subTest(contra=contra, shift=shift, static=static, lit=lit):
                            got = eng.value(eng._tree(eng.values, "te_demog_means"))
                            self.assertAlmostEqual(got, demographics_model.means(inp), places=9)


class TestGiniBands(unittest.TestCase):
    """The generated wealth-band effects (§4.1, wealth bands): each pop's band and income, the
    store, and the formula. Since 2026-10-10 (high wealth) the bands run five levels wide to the top
    level, income is uncapped and summed in units of P.GINI_INCOME_UNIT, and a state stores only the
    bands it has people in, beside its layout (te_dg_gini_layout)."""

    @classmethod
    def setUpClass(cls):
        import demographics_harness
        cls.costs = demographics_harness.buy_package_costs()

    def walk(self, pops, truncate=False):
        """[(people, wealth)] through the walk's sums: {band: (people, income)} for the bands hit."""
        eng = _Engine({}, truncate=truncate)
        eng.call("te_demog_gini_band_init")
        for size, wealth in pops:
            eng.fixtures.update(total_size=float(size), wealth=float(wealth))
            eng.call("te_demog_gini_band_add")
        return {k: (eng.locals[f"te_dg_w_gn{k}"], eng.locals[f"te_dg_w_gy{k}"])
                for k in range(1, P.GINI_BANDS + 1) if eng.locals[f"te_dg_w_gn{k}"]}

    def income(self, size, wealth):
        """the stand-in's income for a pop, in the census's units"""
        return size * demographics_model.stand_in_income(wealth, self.costs) / P.GINI_INCOME_UNIT

    def test_every_wealth_lands_in_the_models_band(self):
        # Review Focus 2, over every level the mod's packages have (NUM_WEALTH_LEVELS = 200)
        for wealth in range(0, P.GINI_TOP_WEALTH + 1):
            hit = self.walk([(10, wealth)])
            self.assertEqual(list(hit), [demographics_model.wealth_band(wealth)], wealth)

    def test_each_pop_adds_the_stand_in_income_in_its_units(self):
        for wealth in range(0, P.GINI_TOP_WEALTH + 1):
            (n, y), = self.walk([(37, wealth)]).values()
            self.assertEqual(n, 37.0)
            self.assertAlmostEqual(y / self.income(37, wealth), 1.0, places=6, msg=str(wealth))

    def test_income_is_not_capped_at_60(self):
        # the cap counted a wealth-109 pop as wealth 60, a 400th of its spending
        per_head = {w: self.walk([(1e5, w)])[demographics_model.wealth_band(w)][1] for w in (60, 61, 100, 150, 200)}
        self.assertGreater(per_head[61], per_head[60])
        self.assertAlmostEqual(per_head[100] / per_head[60], self.costs[100] / self.costs[60], places=4)
        self.assertAlmostEqual(per_head[200] * P.GINI_INCOME_UNIT / 1e5, self.costs[200] / 100, places=2)
        # a wealth above the top level (none exists) is held at the top level's spending
        self.assertEqual(self.walk([(1e5, 260)])[P.GINI_BANDS][1], per_head[200])

    def test_the_old_income_value_is_gone(self):
        # the leaf of the band tree computes the income: no second chain of wealth tests per pop
        for path in DEMOG_FILES:
            self.assertNotIn("te_demog_pop_income", _text(path), path.name)

    def gini(self, bands, truncate=False):
        eng = _Engine({}, truncate=truncate)
        for k in range(1, P.GINI_BANDS + 1):
            n, y = bands.get(k, (0.0, 0.0))
            eng.locals[f"te_dg_g_n{k}"], eng.locals[f"te_dg_g_y{k}"] = float(n), float(y)
        eng.call("te_demog_gini_from_locals")
        return eng.vars["te_dg_gini"]

    def test_the_formula_matches_the_model(self):
        rng = random.Random(11)
        for _ in range(200):
            bands, per_head = {}, 0.0
            for k in range(1, P.GINI_BANDS + 1):
                per_head += rng.uniform(0.0, 30.0)          # bands follow income
                n = rng.choice([0, rng.randint(1, 200000)])
                bands[k] = (n, n * per_head)
            want = demographics_model.shown_gini(demographics_model.grouped_gini(list(bands.values())))
            self.assertAlmostEqual(self.gini(bands), want, places=9)

    def test_nobody_or_no_income_or_one_band_shows_the_floor(self):
        # Review Focus 3 and 4: a computed Gini of 0, shown as 1 - X
        floor = 1 - P.GINI_SHOWN_EQUALITY
        self.assertAlmostEqual(self.gini({}), floor, places=9)
        self.assertAlmostEqual(self.gini({1: (500, 0), 2: (20, 0)}), floor, places=9)
        self.assertAlmostEqual(self.gini({7: (1000, 4321)}), floor, places=9)

    def through_the_script(self, pops, truncate):
        """[(people, wealth)] walked, then the formula over the bands it filled: the shown Gini"""
        return self.gini(self.walk(pops, truncate=truncate), truncate=truncate)

    def by_the_model(self, pops):
        bands = {}
        for size, wealth in pops:
            k = demographics_model.wealth_band(wealth)
            n, y = bands.get(k, (0.0, 0.0))
            bands[k] = (n + size, y + self.income(size, wealth))
        return demographics_model.shown_gini(demographics_model.grouped_gini(list(bands.values())))

    def test_a_china_sized_country_keeps_its_precision(self):
        # Review Focus 5: 4e8 people, most of them poor, with the engine's fixed point
        pops = [(3.2e8, 3), (6e7, 9), (2e7, 45), (1e6, 60), (2e5, 90)]
        self.assertAlmostEqual(self.through_the_script(pops, True), self.by_the_model(pops), places=4)

    def test_the_largest_country_at_the_top_level_fits_the_fixed_point(self):
        """Values are i64 x 1e-5, at most about 9.2e13 (_Engine asserts it under truncate). The fast run's
        whole world, 6.9e9 people, at wealth 200 (9.5e8 a head) in one country sums to 6.6e13 units. Each
        pop's people divide by the unit before they multiply: 1e9 x 9.5e8 would be 9.5e17."""
        pops = [(1.16e9, 200)] * 5 + [(1.1e9, 1)]
        got = self.through_the_script(pops, True)
        self.assertAlmostEqual(got, self.by_the_model(pops), places=4)
        y = self.walk([(6.9e9, 200)], truncate=True)[P.GINI_BANDS][1]
        self.assertAlmostEqual(y / self.income(6.9e9, 200), 1.0, places=6)
        self.assertLess(y, (2 ** 63 - 1) / 1e5)

    def test_a_small_poor_state_keeps_its_precision(self):
        """The census's smallest step of income is 1 a pop (1e-5 of the unit), cut toward zero: a pop of
        one person at wealth 3 (1.86) keeps 1, 46% less, and no pop is cut to 0 (wealth 1 is 1.51 a head).
        The cut takes more from poorer pops, so a small state usually reads slightly high: this one by
        0.0002. Across the 3,903 states of the 1836, 1887, 1953 and fast-run saves the largest miss is
        0.0021; only a state made of one-person pops goes further, 0.02-0.045 high (review of #867)."""
        pops = [(3 + 7 * i, i % 9) for i in range(40)] + [(12, 30), (2, 55)]
        self.assertAlmostEqual(self.through_the_script(pops, True), self.by_the_model(pops), delta=0.002)

    def test_an_1836_state_reads_as_before(self):
        """Below wealth 60 the bands and the stand-in's pieces are the old ones: only the units change,
        and a share does not depend on them."""
        pops = [(250_000, 2), (120_000, 4), (40_000, 7), (9_000, 13), (3_000, 22), (800, 38), (120, 47)]
        old = {}
        for n, w in pops:
            k = demographics_model.wealth_band(w)
            a, b = old.get(k, (0.0, 0.0))
            old[k] = (a + n, b + n * demographics_model.stand_in_income(w, self.costs))   # old units
        want = demographics_model.shown_gini(demographics_model.grouped_gini(list(old.values())))
        self.assertAlmostEqual(self.through_the_script(pops, True), want, delta=0.0005)

    def test_the_store_keeps_the_bands_with_people_and_marks_the_layout(self):
        eng = _Engine({})
        bands = {2: (9e5, 1.4), 3: (2e5, 0.5), 13: (4e3, 0.37), 30: (12.0, 0.5)}
        eng.call("te_demog_gini_band_init")
        for k, (n, y) in bands.items():
            eng.locals[f"te_dg_w_gn{k}"], eng.locals[f"te_dg_w_gy{k}"] = n, y
        # a save from before: 14 bands, every one stored, and the strata sums before them
        old = ("te_dg_n_lo", "te_dg_n_mi", "te_dg_n_up", "te_dg_y_lo", "te_dg_y_mi", "te_dg_y_up")
        eng.vars.update({name: 1.0 for name in old})
        eng.vars.update({f"te_dg_g{s}{k}": 5.0 for k in range(1, 15) for s in "ny"})
        eng.call("te_demog_gini_band_store")
        self.assertEqual(eng.vars["te_dg_gini_layout"], P.GINI_LAYOUT)
        for k in range(1, P.GINI_BANDS + 1):
            if k in bands:
                self.assertEqual((eng.vars[f"te_dg_gn{k}"], eng.vars[f"te_dg_gy{k}"]), bands[k], k)
            else:
                self.assertNotIn(f"te_dg_gn{k}", eng.vars, "an empty band is not stored: save size")
                self.assertNotIn(f"te_dg_gy{k}", eng.vars)
        for name in old:
            self.assertNotIn(name, eng.vars)
        eng.locals.clear()
        eng.call("te_demog_state_gini")
        want = demographics_model.shown_gini(demographics_model.grouped_gini(list(bands.values())))
        self.assertAlmostEqual(eng.vars["te_dg_gini"], want, places=9)

    def test_the_layout_marker_is_the_params(self):
        store = _block(_text(GENERATED_EFFECTS), "te_demog_gini_band_store")
        self.assertIn(f"set_variable = {{ name = te_dg_gini_layout value = {P.GINI_LAYOUT} }}", store)
        add = _block(_text(GENERATED_EFFECTS), "te_demog_gini_band_add_state")
        self.assertIn(f"var:te_dg_gini_layout = {P.GINI_LAYOUT}", add)

    def test_every_band_read_is_guarded_by_has_variable(self):
        """A state stores only the bands it has people in, so every read of one sits inside an if or
        else_if whose limit asks has_variable for that band (an else, or a guard on another band, is
        no guard). Walks every scripted effect and script value of the census, not only the two readers."""
        band = re.compile(r"var:te_dg_g([ny])(\d+)")

        def reads(items, guards):
            for key, _, arg in items:
                if band.fullmatch(key):
                    yield key, guards
                if isinstance(arg, str):
                    if band.fullmatch(arg):
                        yield arg, guards
                    continue
                inner = guards
                if key in ("if", "else_if"):
                    inner = guards | {v for k, _, v in _find_all(arg, "limit") if k == "has_variable"}
                    yield from reads(_find_all(arg, "limit"), guards)
                    arg = [i for i in arg if i[0] != "limit"]
                yield from reads(arg, inner)

        def _find_all(items, key):
            return [x for k, _, v in items if k == key for x in v]

        found = {}
        for path in DEMOG_FILES:
            for name, _, body in _parse_script(_text(path)):
                if not isinstance(body, list):
                    continue
                for read, guards in reads(body, frozenset()):
                    want = "te_dg_gn" + band.fullmatch(read).group(2)
                    self.assertIn(want, guards, f"{path.name}: {name} reads {read} outside has_variable = {want}")
                    found.setdefault(name, set()).add(read)
        every = {f"var:te_dg_g{s}{k}" for k in range(1, P.GINI_BANDS + 1) for s in "ny"}
        self.assertEqual(found.get("te_demog_gini_band_load"), every)
        self.assertEqual(found.get("te_demog_gini_band_add_state"), every)
        self.assertEqual(set(found), {"te_demog_gini_band_load", "te_demog_gini_band_add_state"},
                         "no other reader of the stored bands")

    def test_a_near_total_inequality_shows_near_1_without_a_cap(self):
        bands = {1: (99, 0.0001), P.GINI_BANDS: (1, 1000)}
        want = demographics_model.shown_gini(demographics_model.grouped_gini(list(bands.values())))
        self.assertGreater(want, 0.98)
        self.assertAlmostEqual(self.gini(bands), want, places=9)

    def test_the_constants_of_the_old_map_are_gone(self):
        self.assertNotIn("te_demog_k_gini", _text(GENERATED_VALUES))
