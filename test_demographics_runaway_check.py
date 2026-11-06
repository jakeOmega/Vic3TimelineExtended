"""The census's runaway tripwire, TE_SELF_CHECK demog_runaway (2026-11-06).

The first 1.15 observer game reached 1923 with East Bengal holding some 9e15 people and every census sum there wrapped
at the script's fixed-point limit; nothing in the saves or logs dated the onset. te_debug_demog_runaway_selfcheck
(te_debug_demog_effects.txt) logs the first census at which a state shows a sign of a runaway, once a state, so the next
run dates it. These tests run the real effect through the registry's interpreter (with the console's effects, whose
debug_log lines it records) on the figures the saves held: East Bengal and Sindh trip it, the sane states of a 2020, a
1940 and the 1926 save don't.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from test_demographics_registry import (  # noqa: E402  (helpers only: no TestCase)
    CONSOLE_EFFECTS, EFFECTS, FAST_EFFECTS, _block, _ConsoleEngine, _text)

CHECK = "te_debug_demog_runaway_selfcheck"

# A sane state at its census under Full: Jiangxi (ZHO) in the 1926 autosave, rounded.
SANE = {
    "te_dg_walk_pop": 52_460_000.0, "te_dg_walk_pop_prev": 52_090_000.0, "te_dg_year": 1926.0,
    "te_dg_provinces": 40.0, "te_dg_e0": 40.0, "te_dg_cbr": 36.0, "te_dg_cdr": 28.0, "te_dg_net_migration": -20_000.0,
    "te_dg_in_crowd": 0.0, "te_dg_m_inf": 0.86, "te_dg_mb": -0.36, "te_dg_md": -0.73, "te_dg_tb_b": 0.68,
    "te_dg_tb_d": 0.40, "te_dg_os_b": 0.0, "te_dg_os_d": 0.31, "te_dg_q_b": -0.025, "te_dg_q_d": 0.0,
    "te_dg_rate_clamp_d": 0.0,
}
# Sindh (F48) in the 1923-01-01 autosave: 1.19 billion people, still in range, with a collapsed life table.
SINDH = {**SANE, "te_dg_walk_pop": 1_191_971_667.0, "te_dg_walk_pop_prev": 1_279_442_741.0, "te_dg_year": 1922.0,
         "te_dg_provinces": 32.0, "te_dg_e0": 0.5, "te_dg_cbr": 0.0, "te_dg_cdr": -473.61,
         "te_dg_net_migration": -10_513_204.607, "te_dg_in_crowd": 91.343, "te_dg_m_inf": 96.7, "te_dg_mb": -0.887,
         "te_dg_md": -1.308, "te_dg_tb_b": 0.0, "te_dg_tb_d": -6.946, "te_dg_os_b": -0.099, "te_dg_os_d": 0.308,
         "te_dg_rate_clamp_d": 1.0}
# East Bengal (BGL) in the same save: the walk's sum wrapped.
EAST_BENGAL = {**SANE, "te_dg_walk_pop": -57_239_296_867_066.9, "te_dg_walk_pop_prev": 41_298_817_440_303.55,
               "te_dg_e0": 0.5, "te_dg_md": -1.277, "te_dg_mb": -0.326}


def _engine(state, full=True, prov_step=0.0):
    """A state's census variables and locals as the check finds them; prov_step None: the state held no census before
    this one, so te_debug_demog_province_change set no te_dg_prov_step."""
    eng = _ConsoleEngine({}, triggers={"te_demog_effects_run": full})
    eng.effects["debug_log_scopes"] = ""  # the scopes' dump after the line: nothing to check here
    eng.vars.update(state)
    if prov_step is not None:
        eng.locals["te_dg_prov_step"] = prov_step
    return eng


def _verdicts(eng):
    return [text for text, _ in eng.logs if "demog_runaway" in text]


class TestTripwire(unittest.TestCase):
    def run_check(self, state, **kw):
        eng = _engine(state, **kw)
        eng.call(CHECK)
        return eng

    def assert_trips(self, state, why, **kw):
        eng = self.run_check(state, **kw)
        self.assertEqual(eng.vars.get("te_dg_chk_runaway"), why)
        self.assertEqual(len(_verdicts(eng)), 1)
        self.assertTrue(_verdicts(eng)[0].startswith("TE_SELF_CHECK BROKEN demog_runaway why="))
        return eng

    def assert_quiet(self, state, **kw):
        eng = self.run_check(state, **kw)
        self.assertNotIn("te_dg_chk_runaway", eng.vars)
        self.assertNotIn("te_dg_chk_runaway_year", eng.vars)
        self.assertEqual(_verdicts(eng), [])

    def test_a_sane_state_is_quiet(self):
        self.assert_quiet(SANE)

    def test_the_sane_extremes_of_three_saves_are_quiet(self):
        """The largest state of a 2020 save (128 million), the most crowded of a 1940 one (Travancore, 1.64), the
        largest births term of a 2020 one (Turkmenia, 4.05), and a state whose deaths term sits below -1 only because
        war lines on top offset it (Queensland, the Philippines' share, 1926)."""
        for state in ({**SANE, "te_dg_walk_pop": 128_000_000.0, "te_dg_walk_pop_prev": 127_000_000.0},
                      {**SANE, "te_dg_in_crowd": 1.64, "te_dg_m_inf": 1.542, "te_dg_e0": 28.1},
                      {**SANE, "te_dg_mb": 4.053},
                      {**SANE, "te_dg_md": -1.565, "te_dg_os_d": 1.02, "te_dg_walk_pop": 24_919.0,
                       "te_dg_walk_pop_prev": 27_520.0}):
            with self.subTest(state=state):
                self.assert_quiet(state)

    def test_east_bengal_trips_on_the_wrapped_sum(self):
        self.assert_trips(EAST_BENGAL, 1)

    def test_sindh_trips_on_its_size_and_its_rates_alone_would_too(self):
        self.assert_trips(SINDH, 2)
        # the same rates in a state of 20 million: the life table had collapsed whatever the size
        self.assert_trips({**SINDH, "te_dg_walk_pop": 20_000_000.0, "te_dg_walk_pop_prev": 19_000_000.0}, 4)

    def test_half_a_billion_people(self):
        self.assert_trips({**SANE, "te_dg_walk_pop": 600_000_000.0, "te_dg_walk_pop_prev": 550_000_000.0}, 2)

    def test_tenfold_in_a_year_without_a_province_change(self):
        jump = {**SANE, "te_dg_walk_pop": 1_300_000.0, "te_dg_walk_pop_prev": 99_000.0}
        self.assert_trips(jump, 3)
        # a merge changes the provinces (Rio Negro's thirteenfold in the 1940 save), and a first census has no record
        self.assert_quiet(jump, prov_step=9.0)
        self.assert_quiet(jump, prov_step=None)
        # from fewer than 10,000 people a tenfold rise says nothing
        self.assert_quiet({**SANE, "te_dg_walk_pop": 90_000.0, "te_dg_walk_pop_prev": 8_000.0})

    def test_each_sign_on_its_own(self):
        for change, why in (({"te_dg_e0": 4.9}, 4), ({"te_dg_rate_clamp_d": 1.0}, 5),
                            ({"te_dg_in_crowd": 5.1}, 6), ({"te_dg_mb": 10.5}, 7)):
            with self.subTest(change=change):
                self.assert_trips({**SANE, **change}, why)

    def test_the_rates_of_a_tiny_state_say_nothing(self):
        for change in ({"te_dg_e0": 0.5}, {"te_dg_rate_clamp_d": 1.0}, {"te_dg_in_crowd": 9.0}, {"te_dg_mb": 20.0}):
            with self.subTest(change=change):
                self.assert_quiet({**SANE, "te_dg_walk_pop": 9_000.0, "te_dg_walk_pop_prev": 9_100.0, **change})

    def test_once_a_state(self):
        eng = self.assert_trips(SINDH, 2)
        self.assertEqual(eng.vars["te_dg_chk_runaway_year"], 1922.0, "a save dates the trip")
        eng.vars.update(te_dg_walk_pop=-1.0, te_dg_year=1923.0)
        eng.call(CHECK)
        self.assertEqual(len(_verdicts(eng)), 1)
        self.assertEqual(eng.vars["te_dg_chk_runaway"], 2)
        self.assertEqual(eng.vars["te_dg_chk_runaway_year"], 1922.0)

    def test_only_under_full(self):
        self.assert_quiet(SINDH, full=False)

    def test_a_state_missing_a_figure_it_prints_is_skipped(self):
        """The line prints every figure the limit checks for, so a state without one (no census terms yet) logs nothing
        rather than a line the engine can't fill."""
        for name in ("te_dg_md", "te_dg_walk_pop_prev", "te_dg_in_crowd"):
            with self.subTest(missing=name):
                self.assert_quiet({k: v for k, v in SINDH.items() if k != name})


class TestText(unittest.TestCase):
    BODY = _block(_text(CONSOLE_EFFECTS), CHECK)

    def test_every_printed_variable_is_checked_first(self):
        printed = set(re.findall(r"THIS\.Var\('(\w+)'\)", self.BODY)) - {"te_dg_chk_runaway"}
        checked = set(re.findall(r"has_variable = (\w+)", self.BODY))
        self.assertTrue(printed)
        self.assertEqual(printed - checked, set())

    def test_names_print_without_markup(self):
        self.assertIn("[THIS.GetState.GetNameNoFormatting]", self.BODY)
        self.assertIn("[THIS.GetState.GetOwner.GetTagName]", self.BODY)
        self.assertNotRegex(self.BODY, r"\.GetName\]|GetOwner\.GetTag\]|\[ROOT\.")

    def test_both_census_sites_call_it_after_the_terms(self):
        for path, effect in ((EFFECTS, "te_demog_state_yearly"), (FAST_EFFECTS, "te_demog_state_clock_step")):
            with self.subTest(effect=effect):
                body = _block(_text(path), effect)
                self.assertEqual(body.count(f"{CHECK} = yes"), 1)
                self.assertLess(body.index("te_demog_rates_refresh = yes"), body.index(f"{CHECK} = yes"))
                self.assertLess(body.index("te_demog_state_census = yes"), body.index(f"{CHECK} = yes"))

    def test_on_the_play_test_list(self):
        doc = _text(ROOT / "docs" / "testing" / "demographics-playtest.md")
        self.assertIn("demog_runaway", doc)


if __name__ == "__main__":
    unittest.main()
