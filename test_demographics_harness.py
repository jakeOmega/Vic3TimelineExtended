"""scripts/analysis/demographics_harness.py: the sketch, the Gini anchor and the replay round trip."""

import copy
import io
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_harness as H  # noqa: E402
import demographics_model as M  # noqa: E402
import demographics_save_inputs as S  # noqa: E402

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

    def _step_lines(self, pop=2_000_000, pop_after=2_010_000, war=500, mig=-3000, logged_mmr=True,
                    drop_after=False):
        """The 31 lines of one in-game step: the model stepped from its own seed.

        logged_mmr False steps the "after" ring with no maternal deaths while the head still logs
        the real rate, so the lines describe a script that skipped them. drop_after writes the
        after cohorts under half a person as 0, as the game drops them.
        """
        inp = M.Inputs(sol=11, literacy=0.35, urban_share=0.3)
        before = M.seed(inp, 1836, pop)
        after = copy.deepcopy(before)
        qf, qm, mmr = M.group_rates(inp)
        mult = M.cause_multipliers(inp)
        work_f, work_m = M.work_split(inp, mult["work"])
        tfr = M.fertility(inp, 40)["tfr"]
        prof = M.migrant_profile(inp)
        M.step(after, inp, 1837, engine_pop=pop_after, war_dead=war, migration=mig,
               rates=(qf, qm, mmr if logged_mmr else 0.0, tfr, prof))
        head = {"pop": pop_after, "war": war, "kills": 0, "mig": mig, "tfr": tfr, "mmr": mmr,
                "m_inf": mult["infection"], "m_ext": mult["external"], "m_chr": mult["chronic"],
                "m_work_f": work_f, "m_work_m": work_m, "profile": prof}
        lines = H.format_replay("TEST", 1837, before, head, after)
        return self._drop_small_cohorts(lines, pop_after) if drop_after else lines

    @staticmethod
    def _drop_small_cohorts(lines, pop_after):
        """The lines with every after-state slot under half a person written as 0, as the game drops them."""
        def zero(m):
            return f"{m.group(1)}=" + ",".join("0" if float(x) * pop_after / 1000.0 < 0.5 else x
                                                for x in m.group(2).split(","))
        return [re.sub(r"\b(f|m)=(\S+)", zero, x) if " after " in x else x for x in lines]

    def _good_lines(self):
        """The 31 lines of one correct in-game step at 2 million people."""
        return self._step_lines()

    def _replay_cli(self, lines, *flags):
        """(exit code, stdout) of `replay` on a log made of these lines."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "debug.log"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = H.main(["replay", str(path), *flags])
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

    def test_replay_cli_catches_a_step_run_without_maternal_deaths(self):
        """Measured at 2 million people: a missing mmr is 0.16% off in the worst slot."""
        lines = self._step_lines(logged_mmr=False)
        code, out = self._replay_cli(lines)
        self.assertEqual(code, 1, out)
        self.assertIn("MISMATCH", out)
        self.assertIn("worst slot error", out)
        code, out = self._replay_cli(lines, "--tolerance", "0.01")   # the old default let it through
        self.assertEqual(code, 0, out)

    def test_replay_cli_accepts_states_of_a_few_thousand_people(self):
        """The game drops a cohort under half a person; at 3,000 people that is above 0.05 per mille."""
        for pop, war, mig in ((3000, 0, -30), (8000, 5, -30)):
            with self.subTest(pop=pop):
                lines = self._step_lines(pop=pop, pop_after=pop + pop // 300, war=war, mig=mig, drop_after=True)
                code, out = self._replay_cli(lines)
                self.assertEqual(code, 0, out)
                self.assertTrue(out.rstrip().endswith("OK"), out)

    def test_replay_still_compares_the_small_cohorts_it_can_see(self):
        """A cohort of a few people that the script got wrong is not hidden by the small-state rule."""
        lines = self._step_lines(pop=3000, pop_after=3010, war=0, mig=-30, drop_after=True)
        self.assertEqual(self._replay_cli(lines)[0], 0)
        blocks = H.parse_replay(lines)
        men = blocks[0]["after"]["m"]
        slot = next(k for k, v in men.items() if 2 <= v * 3010 / 1000 <= 30)   # 2 to 30 people
        men[slot] *= 1.5
        self.assertGreater(H.replay_block(blocks[0]), 0.2)

    def _scale_before(self, lines, k):
        """The lines with every `before` slot and the pool multiplied by k (a before-state not summing to 1000)."""
        def scale(line):
            return re.sub(r"\b(pool_f|pool_m|f|m)=([^ ]+)",
                          lambda m: f"{m.group(1)}=" + ",".join(H._fmt(float(x or 0) * k) for x in m.group(2).split(",")),
                          line)
        return [scale(x) if " before " in x else x for x in lines]

    def test_replay_cli_rejects_a_before_state_that_does_not_sum_to_one_thousand(self):
        lines = self._good_lines()
        code, out = self._replay_cli(self._scale_before(lines, 0.9))
        self.assertEqual(code, 1, out)
        self.assertIn("MISMATCH (malformed: before-state sums to 900", out)
        self.assertIn("\u2030", out)
        code, out = self._replay_cli(self._scale_before(lines, 1.005))   # within 1%: the rounding the log carries
        self.assertEqual(code, 0, out)

    def test_a_before_state_with_missing_slots_is_incomplete_not_a_wrong_sum(self):
        lines = self._good_lines()
        code, out = self._replay_cli(lines[:3] + lines[4:])   # the third `before` line is gone
        self.assertEqual(code, 1, out)
        self.assertIn("MISMATCH (incomplete:", out)
        self.assertNotIn("sums to", out)

    def _cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = H.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    @unittest.skipUnless(SLICE.exists(), "fixture written in Task 3")
    def test_gini_on_the_slice(self):
        code, out, _err = self._cli("gini", str(SLICE), "--tag", "GBR")
        self.assertEqual(code, 0)
        self.assertIn("GINI_SCALE for GBR = 0.52:", out)
        grouped = re.search(r"^GBR grouped (\d\.\d+)", out, re.M)
        self.assertIsNotNone(grouped, out)
        self.assertGreater(float(grouped.group(1)), 0)

    @unittest.skipUnless(SLICE.exists(), "fixture written in Task 3")
    def test_gini_exits_1_when_the_anchor_tag_has_no_pops(self):
        code, out, err = self._cli("gini", str(SLICE), "--tag", "GBR", "--anchor-tag", "XXX")
        self.assertEqual(code, 1, out)
        self.assertIn("XXX", err)
        self.assertNotIn("GINI_SCALE", out)

    def test_save_commands_exit_1_on_a_non_plain_text_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "autosave.v3"
            path.write_bytes(b"SAV0103\n\xffU\x01\x00PK\x03\x04\x00\x00")
            for argv in (("gini", str(path)), ("seed", str(path), "--tag", "GBR"), ("inputs", str(path)),
                         ("natural-change", str(path), str(path))):
                with self.subTest(argv[0]):
                    code, out, err = self._cli(*argv)
                    self.assertEqual(code, 1, out)
                    self.assertIn("autosave.v3", err)
                    self.assertEqual(out, "")

    @unittest.skipUnless(SLICE.exists(), "fixture written in Task 3")
    def test_seed_uses_the_pop_weighted_wealth_term(self):
        c = S.country_inputs(S.read_sections(SLICE))["GBR"]
        inp = H.inputs_for(c)
        self.assertAlmostEqual(inp.wealth_tfr, c.wealth_tfr)
        self.assertNotAlmostEqual(c.wealth_tfr, M.wealth_tfr(c.sol), places=3)   # the curve is not linear here
        code, out, _err = self._cli("seed", str(SLICE), "--tag", "GBR")
        self.assertEqual(code, 0)
        self.assertIn(f"(wealth {c.wealth_tfr:.2f} x factor", out)
