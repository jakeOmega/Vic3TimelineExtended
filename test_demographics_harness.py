"""scripts/analysis/demographics_harness.py: the sketch, the Gini anchor and the replay round trip."""

import copy
import io
import re
import sys
import tempfile
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
        self.assertEqual(H._ungroup("0_0_500.5"), 500.5)
        self.assertEqual(H._ungroup("1_2_3.25"), 1_002_003.25)

    def _good_lines(self):
        """The 31 lines of one correct in-game step: the model stepped from its own seed."""
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
        return H.format_replay("TEST", 1837, before, head, after)

    def _replay_cli(self, lines):
        """(exit code, stdout) of `replay` on a log made of these lines."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "debug.log"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = H.main(["replay", str(path)])
        return code, out.getvalue()

    def test_replay_cli_accepts_a_complete_block(self):
        code, out = self._replay_cli(["[12:00:00][script.cpp:1]: " + x for x in self._good_lines()])
        self.assertEqual(code, 0, out)
        self.assertIn("TEST 1837", out)
        self.assertTrue(out.rstrip().endswith("OK"), out)

    def test_replay_cli_rejects_a_block_missing_its_last_after_lines(self):
        lines = self._good_lines()
        self.assertEqual(len(lines), 31)
        code, out = self._replay_cli(lines[:-5])
        self.assertEqual(code, 1, out)
        self.assertIn("MISMATCH (incomplete:", out)
        self.assertIn("after", out)

    def test_replay_cli_rejects_a_block_with_no_after_lines(self):
        code, out = self._replay_cli(self._good_lines()[:16])
        self.assertEqual(code, 1, out)
        self.assertIn("MISMATCH (incomplete:", out)
        self.assertIn("after pool missing", out)

    def test_replay_cli_rejects_a_block_without_a_pool(self):
        lines = [re.sub(r" pool_f=\S* pool_m=\S* pool_age=\S*", "", x) for x in self._good_lines()]
        code, out = self._replay_cli(lines)
        self.assertEqual(code, 1, out)
        self.assertIn("MISMATCH (incomplete:", out)

    def test_replay_cli_reports_a_malformed_block_and_goes_on(self):
        good = self._good_lines()
        bad_tfr = [re.sub(r"tfr=\S*", "tfr=", good[0], count=1)] + good[1:]
        bad_pop = [good[0].replace("pop=", "pop=0_x_5 old=", 1)] + good[1:]
        no_mig = [re.sub(r" mig=\S*", "", good[0])] + good[1:]
        bad_slot = good[:1] + [good[1].replace("f=", "f=abc,", 1)] + good[2:]
        for label, block in (("blank tfr", bad_tfr), ("non-numeric pop", bad_pop),
                             ("no mig", no_mig), ("bad slot", bad_slot)):
            with self.subTest(label):
                code, out = self._replay_cli(block + good)   # the good block after it still runs
                self.assertEqual(code, 1, out)
                self.assertIn("MISMATCH (malformed:", out)
                self.assertEqual(len(out.splitlines()), 2, out)
                self.assertTrue(out.rstrip().endswith("OK"), out)

    def test_replay_cli_with_a_fractional_people_count(self):
        good = self._good_lines()
        head = re.sub(r"war=\S*", "war=0_0_500.5", good[0], count=1)
        code, out = self._replay_cli([head] + good[1:])
        self.assertNotIn("malformed", out)

    @unittest.skipUnless(SLICE.exists(), "fixture written in Task 3")
    def test_gini_on_the_slice(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["gini", str(SLICE), "--tag", "GBR"]), 0)
        self.assertIn("GBR grouped", out.getvalue())
