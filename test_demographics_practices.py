"""scripts/analysis/demographics_practices.py: Late Marriage and Birth Spacing in the harness
(docs/superpowers/plans/2026-10-11-demographics-late-marriage.md, Tasks 3-5)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
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
