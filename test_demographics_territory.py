"""The census without its size test, and its province line (owner, 2026-10-20).

A census pulse no longer seeds a state again when its people moved more than a quarter in a year: that rule took such a
move for a state merged or split, and in the owner's 2057 game it fired only on migration. In its place the census
stores the state's provinces at each pulse (te_dg_provinces, from te_demog_state_provinces) and logs a TE_INFO line
when they changed, so a play-test learns whether the engine merges or splits states at all. The line changes no number.
The script runs through test_demographics_registry's interpreter; the big move's step against the model is
TestCohortScript.test_a_big_move_is_stepped_and_booked_as_migration there."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from test_demographics_registry import (  # noqa: E402  (helpers and paths only: no TestCase)
    CONSOLE_EFFECTS, EFFECTS, _block, _console_blocks, _ConsoleEngine, _Engine, _parse_script, _text)

TERRITORY_VALUES = ROOT / "common" / "script_values" / "te_demog_territory_values.txt"
CONSOLE_VALUES = ROOT / "common" / "script_values" / "te_debug_demog_values.txt"
LINE = "te_debug_demog_province_change"
# the census pulse with its seed and step stubbed: which ran, and nothing else
STUBS = {"te_demog_seed": "set_variable = { name = did value = 1 }",
         "te_demog_step": "set_variable = { name = did value = 2 }"}


def _pulse(provinces, stored=None, census=1836.0, pop=1000.0, pop_last=1000.0, engine=_Engine, effects=None):
    """te_demog_state_census in 1837 for a state with `provinces` provinces now and `stored` at its last pulse (None:
    no stored count); census None: no census yet."""
    eng = engine({"year": 1837.0, "state_population": pop, "te_demog_state_provinces": float(provinces)},
                 triggers={"te_demog_cohorts_run": True}, effects={**STUBS, **(effects or {})})
    if census is not None:
        eng.vars.update(te_dg_year=census, te_dg_raw=900.0, te_dg_pop_last=pop_last)
    if stored is not None:
        eng.vars["te_dg_provinces"] = float(stored)
    eng.call("te_demog_state_census")
    return eng


def _console(provinces, stored, pop=1000.0, pop_last=1000.0, census=1836.0):
    """The same pulse with the line's own text run: _ConsoleEngine records each debug_log with the variables then."""
    def make(fixtures, triggers=None, effects=None):
        eng = _ConsoleEngine(fixtures, triggers=triggers, effects=effects)
        eng.effects.update(STUBS)
        eng.effects["debug_log_scopes"] = ""
        return eng
    return _pulse(provinces, stored, census=census, pop=pop, pop_last=pop_last, engine=make)


def _effect_keys(items):
    """Every effect key in a parsed body, its if branches' included (a limit's triggers left out)."""
    keys = []
    for key, _op, arg in items:
        keys.append(key)
        if key in ("if", "else_if", "else") and isinstance(arg, list):
            keys.extend(_effect_keys([i for i in arg if i[0] != "limit"]))
    return keys


class TestNoSizeTest(unittest.TestCase):
    def test_the_census_has_no_size_test(self):
        """The 25% rule and its locals are gone, Internal Resettlement's exclusion with them; the hard necessities
        stay: a census more than a year old, an emptied ring with people, a seed made off the pulse."""
        code = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_state_census"))
        for gone in ("te_dg_over", "te_dg_under", "te_dg_pop_last", "te_demog_rs_known_change", "multiply"):
            self.assertNotIn(gone, code)
        for kept in ("local_var:te_dg_gap > 1", "var:te_dg_raw < 1", "state_population > 0",
                     "has_variable = te_dg_reseed", "local_var:te_dg_gap = 1"):
            self.assertIn(kept, code)

    def test_people_far_off_the_last_census_step(self):
        for pop in (5740.0, 1251.0, 749.0, 250.0, 1000.0):
            with self.subTest(pop=pop):
                self.assertEqual(_pulse(10, 10, pop=pop).vars["did"], 2)

    def test_the_hard_necessities_still_seed(self):
        self.assertEqual(_pulse(10, 10, census=1834.0).vars["did"], 1, "a census gap")
        eng = _Engine({"year": 1837.0, "state_population": 1000.0}, triggers={"te_demog_cohorts_run": True},
                      effects=STUBS)
        eng.vars.update(te_dg_year=1836.0, te_dg_raw=0.5, te_dg_pop_last=1000.0)
        eng.call("te_demog_state_census")
        self.assertEqual(eng.vars["did"], 1, "an emptied ring with people")
        eng = _Engine({"year": 1837.0, "state_population": 1000.0}, triggers={"te_demog_cohorts_run": True},
                      effects=STUBS)
        eng.vars.update(te_dg_year=1836.0, te_dg_raw=900.0, te_dg_pop_last=1000.0, te_dg_reseed=1.0)
        eng.call("te_demog_state_census")
        self.assertEqual(eng.vars["did"], 1, "a seed made off the pulse")

    def test_the_known_moves_value_went_with_the_test(self):
        """te_demog_rs_known_change had no reader but the size test; the booking reads te_demog_rs_take's counters."""
        for path in ROOT.glob("common/**/*.txt"):
            self.assertNotIn("te_demog_rs_known_change", _text(path), path.name)


class TestProvinceLine(unittest.TestCase):
    def test_the_count_is_a_value_block_of_every_province(self):
        """The base game counts a state's provinces so (occupation_values.txt, root = state). As an effect
        every_province is registered from a province, so no census effect iterates provinces itself."""
        body = re.sub(r"\s+", " ", _block(_text(TERRITORY_VALUES), "te_demog_state_provinces"))
        self.assertEqual(body.strip(), "value = 0 every_province = { add = 1 }")
        for path in ROOT.glob("common/scripted_effects/te_*demog*.txt"):
            self.assertNotIn("every_province", re.sub(r"#[^\n]*", "", _text(path)), path.name)

    def test_each_census_pulse_stores_the_count(self):
        for kwargs in (dict(census=None), dict(stored=8), dict(stored=8, census=1837.0), dict(stored=8, census=1834.0)):
            with self.subTest(**kwargs):
                self.assertEqual(_pulse(12, **kwargs).vars["te_dg_provinces"], 12.0)
        eng = _Engine({"year": 1837.0, "state_population": 1000.0, "te_demog_state_provinces": 12.0},
                      triggers={"te_demog_cohorts_run": False}, effects=STUBS)
        eng.call("te_demog_state_census")
        self.assertNotIn("te_dg_provinces", eng.vars, "no census, no count")

    def test_the_line_logs_a_change_only(self):
        for stored, logged in ((10, True), (14, True), (12, False), (None, False)):
            with self.subTest(stored=stored):
                eng = _console(12, stored, pop=2500.0, pop_last=1000.0)
                lines = [(s, v) for s, v in eng.logs if s.startswith("TE_INFO demog_province_change")]
                self.assertEqual(len(lines), 1 if logged else 0)
                if logged:
                    at = lines[0][1]
                    # what the line prints, as it stood: the old count and the last census's people
                    self.assertEqual(at["te_dg_provinces"], float(stored))
                    self.assertEqual(at["te_dg_pop_last"], 1000.0)
                    self.assertNotIn("did", at, "before the seed or step")

    def test_the_line_changes_no_number(self):
        """Its body only logs; and the census decides the same with or without a change of provinces."""
        # each debug_log string a token, as the console engine reads it
        keys = _effect_keys(_parse_script(_console_blocks()[0][LINE]))
        self.assertEqual(set(keys), {"if", "debug_log", "debug_log_scopes"})
        for pop in (1000.0, 5740.0, 250.0):
            with self.subTest(pop=pop):
                same, changed = _console(10, 10, pop=pop), _console(13, 10, pop=pop)
                self.assertEqual(len(changed.logs), 1)
                self.assertEqual({k: v for k, v in same.vars.items() if k != "te_dg_provinces"},
                                 {k: v for k, v in changed.vars.items() if k != "te_dg_provinces"})

    def test_the_line_prints_from_the_state(self):
        """debug_log reads only THIS's variables and script values (scripting_best_practices.md): the old and new
        counts, the people at the last census and now, the owner's tag, and the scope dump as a fallback."""
        text = _text(CONSOLE_EFFECTS)
        line = re.search(r'debug_log = "(TE_INFO demog_province_change[^"]*)"', text).group(1)
        for read in ("[THIS.Var('te_dg_provinces').GetValue|0]", "[THIS.ScriptValue('te_demog_state_provinces')|0]",
                     "[THIS.Var('te_dg_pop_last').GetValue|0]",
                     "[THIS.ScriptValue('te_debug_demog_province_people')|0]", "[THIS.GetState.GetOwner.GetTag]"):
            self.assertIn(read, line)
        self.assertNotIn("local_var", line, "locals don't reach a debug_log line")
        self.assertIn("debug_log_scopes = yes", _block(text, LINE))
        people = re.sub(r"\s+", " ", _block(_text(CONSOLE_VALUES), "te_debug_demog_province_people")).strip()
        self.assertEqual(people, "value = state_population")

    def test_called_before_the_seed_or_step(self):
        """So te_dg_pop_last and te_dg_provinces are still the last census's when it prints."""
        body = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_state_census"))
        call = body.index(f"{LINE} = yes")
        census = body.index("te_demog_has_census")
        self.assertLess(census, call)
        self.assertLess(call, body.rindex("te_demog_seed = yes"))
        self.assertLess(call, body.index("te_demog_step = yes"))
        self.assertLess(body.index("te_demog_step = yes"),
                        body.index("set_variable = { name = te_dg_provinces value = local_var:te_dg_prov }"))


if __name__ == "__main__":
    unittest.main()
