"""scripts/analysis/demographics_practices.py: Late Marriage and Birth Spacing in the harness
(docs/superpowers/plans/2026-10-11-demographics-late-marriage.md, Tasks 3-5)."""

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_practices as DP  # noqa: E402


def _state(sid, state_region, strategic_region, people=1000.0, tag="TST", incorporated=True, **inp):
    return DP.PracticeState(sid, tag, state_region, strategic_region, people, incorporated, M.Inputs(**inp))


class TestInputs(unittest.TestCase):
    def test_table_shares_are_each_states_start(self):
        states = [_state("1", "STATE_POSEN", "region_eastern_europe"), _state("2", "STATE_KANTO", "region_northeast_asia"),
                  _state("3", "STATE_UNKNOWN", "")]
        got = DP.table_shares(states)
        self.assertEqual(got["1"], {"lm": 0.8, "bs": 0.0})
        self.assertEqual(got["2"], {"lm": 0.0, "bs": 1.0})
        self.assertEqual(got["3"], {"lm": 0.0, "bs": 0.0})

    def test_read_shares_round_trips_the_replays_file(self):
        data = {"1837": {"1": {"lm": 1.0, "bs": 0.0, "people": 5.0, "state_region": "STATE_X",
                               "strategic_region": "region_x", "target_lm": 1.0, "target_bs": 0.0}}}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(data, fh)
        try:
            self.assertEqual(DP.read_shares(fh.name), {1837: {"1": {"lm": 1.0, "bs": 0.0}}})
        finally:
            Path(fh.name).unlink()


class TestReplay(unittest.TestCase):
    """The drift replay (spec 5.1 item 5): both shares stepped a year at a time through a run's saves."""

    def test_states_seed_from_the_table_in_any_order(self):
        # a Baltic state beside a Russian one: no cascade (the plan's D5), whatever order the states come in
        for order in ((0, 1), (1, 0)):
            states = [_state("1", "STATE_RIGA", "region_eastern_europe"), _state("2", "STATE_PSKOV", "region_russia")]
            got = DP.replay([(1837, [states[i] for i in order])])
            self.assertEqual((got[1837]["1"]["lm"], got[1837]["2"]["lm"]), (0.8, 0.0), order)

    def test_a_new_state_takes_its_siblings_share(self):
        first = [_state("1", "STATE_POSEN", "region_eastern_europe", people=3000.0,
                        mods={P.CONTRACEPTION_TYPE: 1.0}, literacy=1.0)]
        later = first + [_state("2", "STATE_POSEN", "region_eastern_europe", people=1000.0)]
        got = DP.replay([(1837, first), (1897, later)])
        sibling, split = got[1897]["1"]["lm"], got[1897]["2"]["lm"]
        self.assertLess(sibling, 0.5, "Posen drifted down with contraception")
        # the split seeds from its sibling's drifted share, then takes one step at its own conditions (no contraception)
        self.assertAlmostEqual(split, sibling, delta=0.05)
        self.assertLess(split, 0.8, "not the 1836 table")

    def test_a_state_seeded_late_with_no_sibling_starts_eroded(self):
        """Review I2: a state that first appears in a late save, with no sibling holding a share, seeds at its start
        less what its conditions have eroded, not at the 1836 custom."""
        late = _state("1", "STATE_KANTO", "region_northeast_asia", literacy=1.0,
                      mods={P.CONTRACEPTION_TYPE: 1.0, P.ACCESS_TYPE: 1.0})
        got = DP.replay([(1950, [late])])
        self.assertEqual(got[1950]["1"]["bs"], 0.0)

    def test_years_between_saves_take_the_earlier_saves_conditions(self):
        before = _state("1", "STATE_KANTO", "region_northeast_asia")
        after = replace(before, inp=replace(before.inp, mods={P.ACCESS_TYPE: 0.5}))
        got = DP.replay([(1837, [before]), (1847, [after])])
        target = M.practice_target("bs", after.inp, 1.0)
        # nine steps at 1837's conditions (target 1: no move), then the 1847 step at 1847's
        self.assertAlmostEqual(got[1847]["1"]["bs"], M.practice_drift(1.0, target), places=9)
        self.assertAlmostEqual(got[1847]["1"]["target_bs"], target, places=9)

    def test_the_gate(self):
        west = _state("1", "STATE_HOME_COUNTIES", "region_western_europe", people=5e6)
        japan = _state("2", "STATE_KANTO", "region_northeast_asia", people=5e6)
        ok = DP.replay([(1837, [west, japan]), (1887, [west, japan])])
        self.assertEqual(DP.replay_gate(ok), [])
        # Japan's spacing eroding from 1837 on (contraception and health care held from the first save): the 1887 save
        # reads it well below its start. Seeded with the conditions already in place it would start eroded, so the
        # first save holds Japan as it was and the eroding conditions come in at the second.
        eroded = replace(japan, inp=replace(japan.inp, mods={P.ACCESS_TYPE: 0.5, P.CONTRACEPTION_TYPE: 1.0},
                                            literacy=1.0))
        bad = DP.replay([(1837, [west, japan]), (1838, [west, eroded]), (1887, [west, eroded])])
        self.assertTrue(any("East Asia" in line for line in DP.replay_gate(bad)))
