"""scripts/analysis/demographics_harness.py: the sketch, the Gini anchor and the replay round trip."""

import copy
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_harness as H  # noqa: E402
import demographics_model as M  # noqa: E402

SLICE = ROOT / "test_fixtures" / "demographics" / "gb_1836_slice.v3"


class TestHarness(unittest.TestCase):
    def test_sketch_runs(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["sketch"]), 0)
        self.assertIn("Britain 1836", out.getvalue())

    def test_buy_package_costs_rise_with_wealth(self):
        costs = H.buy_package_costs()
        self.assertEqual(len(costs), 200)
        self.assertLess(costs[1], costs[20])
        self.assertEqual(H.income_proxy(150, costs), costs[60])

    def test_replay_round_trip(self):
        inp = M.Inputs(sol=11, literacy=0.35, urban_share=0.3)
        before = M.seed(inp, 1836, 2_000_000)
        after = copy.deepcopy(before)
        qf, qm, mmr = M.group_rates(inp)
        mult = M.cause_multipliers(inp)
        work_f, work_m = M.work_split(inp, mult["work"])
        tfr = M.fertility(inp, 40)["tfr"]
        prof = M.migrant_profile(inp)
        M.step(after, inp, 1837, engine_pop=2_010_000, war_dead=500, migration=-3000,
               rates=(qf, qm, mmr, tfr, prof))
        head = {"pop": 2_010_000, "war": 500, "kills": 0, "mig": -3000, "tfr": tfr, "mmr": mmr,
                "m_inf": mult["infection"], "m_ext": mult["external"], "m_chr": mult["chronic"],
                "m_work_f": work_f, "m_work_m": work_m, "profile": prof}
        lines = H.format_replay("TEST", 1837, before, head, after)
        self.assertEqual(len(lines), 31)
        self.assertIn("pop=2_10_0", lines[0])
        blocks = H.parse_replay(lines)
        self.assertEqual(len(blocks), 1)
        self.assertLess(H.replay_block(blocks[0]), 0.001)

    def test_replay_catches_a_wrong_step(self):
        inp = M.Inputs()
        before = M.seed(inp, 1836, 1_000_000)
        after = copy.deepcopy(before)
        M.step(after, inp, 1837, engine_pop=1_000_000)
        after.f[(1837 - 30) % 150] *= 1.5   # the script got one cohort wrong
        qf, qm, mmr = M.group_rates(inp)
        mult = M.cause_multipliers(inp)
        work_f, work_m = M.work_split(inp, mult["work"])
        head = {"pop": 1_000_000, "war": 0, "kills": 0, "mig": 0, "tfr": M.fertility(inp, 40)["tfr"],
                "mmr": mmr, "m_inf": mult["infection"], "m_ext": mult["external"], "m_chr": mult["chronic"],
                "m_work_f": work_f, "m_work_m": work_m, "profile": M.migrant_profile(inp)}
        blocks = H.parse_replay(H.format_replay("TEST", 1837, before, head, after))
        self.assertGreater(H.replay_block(blocks[0]), 0.2)

    def test_grouped_numbers(self):
        self.assertEqual(H._grouped(2_803_898), "2_803_898")
        self.assertEqual(H._ungroup("0_490_84"), 490_084)
        self.assertEqual(H._ungroup("-0_3_0"), -3000)

    @unittest.skipUnless(SLICE.exists(), "fixture written in Task 3")
    def test_gini_on_the_slice(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["gini", str(SLICE), "--tag", "GBR"]), 0)
        self.assertIn("GBR grouped", out.getvalue())
