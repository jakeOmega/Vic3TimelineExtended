"""scripts/analysis/demographics_harness.py: the sketch, the Gini anchor and the replay round trip."""

import copy
import io
import math
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
import demographics_modifiers as DM  # noqa: E402
import demographics_save_inputs as S  # noqa: E402

SLICE = ROOT / "test_fixtures" / "demographics" / "gb_1836_slice.v3"
ANCHORS = ROOT / "test_fixtures" / "demographics" / "history_anchors.csv"
CONSOLE = ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"
GENERATED_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_generated_effects.txt"
LOG_PREFIX = "[12:00:00][jomini_effect_impl.cpp:454]: common/scripted_effects/te_debug_demog_effects.txt:66: "


class TestHarness(unittest.TestCase):
    def test_sketch_runs(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["sketch"]), 0)
        self.assertIn("Britain 1836", out.getvalue())

    def test_medicine_anchors_hold(self):
        # every scenario of `medicine` is inside its band with the game files' values
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["medicine"]), 0, out.getvalue())
        for label, _kw, _targets in H.MEDICINE_SCENARIOS:
            self.assertIn(label, out.getvalue())
        self.assertNotIn(" OUT", out.getvalue())

    def test_fertility_anchors_hold(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["fertility"]), 0, out.getvalue())
        for label, _kw, _band in H.FERTILITY_SCENARIOS:
            self.assertIn(label, out.getvalue())
        self.assertNotIn(" OUT", out.getvalue())

    def test_fertility_rows_match_the_models_steady_state(self):
        # the command's shortcut (fertility at the scenario's own e0) is what a constant run settles on
        label, kw, _band = H.FERTILITY_SCENARIOS[1]
        inp = H.scenario_inputs(DM.load_carriers(), **kw)
        _ring, last = M.run_constant(inp, years=200)
        row = next(r for r in H.fertility_rows() if r[0] == label)
        self.assertAlmostEqual(row[1], last["tfr"], places=2)

    @unittest.skipUnless(SLICE.exists(), "fixture written in Task 3")
    def test_history_on_the_slice(self):
        # the model's figures for Britain beside the anchors nearest the save's year
        code, out, err = self._cli("history", str(SLICE), "--anchors", str(ANCHORS), "--year", "1836")
        self.assertEqual(code, 0, err)
        line = next(l for l in out.splitlines() if l.startswith("GBR"))
        self.assertRegex(line, r"model e0 \d+\.\d")
        self.assertIn("history e0 41 (1838)", line)
        self.assertIn("imr 153", line)
        self.assertIn("tfr 5.1", line, "Gapminder's children per woman beside the model's")
        self.assertRegex(line, r"people \+0\.8\d%")       # 1820-1850, the benchmarks around 1836
        self.assertRegex(out, r"world .* e0 \d+\.\d")

    def test_history_takes_each_states_own_rates(self):
        """The census works state by state, and the poverty term bends at SoL 9: a country with states either
        side of it gets the people-weighted mean of their own rates, not the rates at its mean SoL (#855's review)."""
        carriers = DM.load_carriers()

        def state(sol, people):
            c = S.CountryInputs("TST")
            c.population, c.sol_x_size, c.wealth_tfr_x_size = people, sol * people, M.wealth_tfr(sol) * people
            c.workforce, c.literate = people / 2, people / 10
            return c

        states = [("1", state(5.0, 1000.0), True), ("2", state(13.0, 1000.0), True)]
        got = H.country_figures(states, carriers)
        each = [H.model_figures(H.inputs_for(s, carriers, incorporated=inc)) for _, s, inc in states]
        for k in ("e0", "imr", "tfr", "r"):
            self.assertAlmostEqual(got[k], (each[0][k] + each[1][k]) / 2, msg=k)
        whole = H.model_figures(H.inputs_for(state(9.0, 2000.0), carriers))
        self.assertGreater(abs(got["e0"] - whole["e0"]), 0.5, "the mean SoL would hide the bend")

    def test_inputs_carry_a_static_means_shift(self):
        c = S.CountryInputs("TST", population=100.0, sol_x_size=1000.0, workforce=50.0, literate=10.0)
        c.means_add = 0.6
        self.assertEqual(H.inputs_for(c, DM.load_carriers()).means_add, 0.6)

    def test_history_prints_the_fertility_anchor(self):
        a = H.read_anchors(ANCHORS)
        self.assertEqual(H.nearest(a["tfr"]["United Kingdom"], 1836, 5), (1836, 5.1))

    def test_inputs_for_passes_a_states_crowding(self):
        """migration_crowding sits on 91% of the 1837 world's people; the history check left it out (2026-10-10)."""
        c = S.CountryInputs("TST")
        c.population, c.sol_x_size, c.wealth_tfr_x_size = 1000.0, 8000.0, M.wealth_tfr(8.0) * 1000.0
        c.workforce, c.literate = 500.0, 100.0
        plain = H.inputs_for(c)
        c.crowding = 0.2   # a 20% migration penalty
        crowded = H.inputs_for(c)
        self.assertEqual(plain.crowding, 0.0)
        self.assertEqual(crowded.crowding, 0.2)
        self.assertLess(H.model_figures(crowded)["e0"], H.model_figures(plain)["e0"] - 1)

    def test_save_year_reads_game_date_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.v3"
            p.write_text('SAV0100x\nmeta_data={\n\tversion="1.14.5"\n\tgame_date=1887.1.1\n}\n', encoding="utf-8")
            self.assertEqual(H.save_year(p), 1887)
            p.write_text("SAV0100x\nmeta_data={\n\tdate=1.1.1\n}\n", encoding="utf-8")
            self.assertIsNone(H.save_year(p), "an ironman save's date= is not the game's year")

    @unittest.skipUnless(SLICE.exists(), "fixture written in Task 3")
    def test_history_prefers_the_saves_own_date_and_reports_its_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            dated = Path(tmp) / "dated.v3"
            dated.write_text(SLICE.read_text(encoding="utf-8").replace("meta_data={\n", "meta_data={\n\tgame_date=1850.1.1\n", 1),
                             encoding="utf-8")
            code, out, _err = self._cli("history", str(dated), "--anchors", str(ANCHORS), "--year", "1836")
            self.assertEqual(code, 0)
            self.assertIn("(1850)", out, "--year only fills in a save with no game_date")
        code, out, err = self._cli("history", str(SLICE), "--anchors", str(ANCHORS))
        self.assertEqual(code, 1)
        self.assertIn("--year", err)
        code, out, err = self._cli("history", str(SLICE), "--anchors", "/nonexistent/anchors.csv", "--year", "1836")
        self.assertEqual(code, 1)
        self.assertIn("anchors.csv", err)
        code, out, err = self._cli("history", str(SLICE), "--anchors", str(ANCHORS), "--year", "1836")
        self.assertIn("Portugal: no anchors", err)

    def test_growth_around_skips_a_zero_benchmark(self):
        self.assertIsNone(H.growth_around({1820: 0.0, 1850: 10.0}, 1836))
        self.assertIsNone(H.growth_around({1820: 10.0, 1850: 0.0}, 1836))

    def test_history_anchors_round_trip(self):
        a = H.read_anchors(ANCHORS)
        self.assertEqual(a["e0"]["United Kingdom"][1838], 41.0)
        self.assertEqual(H.nearest(a["e0"]["United Kingdom"], 1836, 15), (1838, 41.0))
        self.assertIsNone(H.nearest(a["e0"]["United Kingdom"], 1870, 15))
        self.assertAlmostEqual(H.growth_around(a["population"]["United Kingdom"], 1860), 100 * math.log(31400 / 27181) / 20)
        self.assertIsNone(H.growth_around(a["population"]["United Kingdom"], 1900))

    def test_adopters_on_the_slice(self):
        # Britain holds Charitable Health System in 1836; Portugal has none
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["adopters", str(SLICE)]), 0)
        self.assertIn("law_charitable_health_system", out.getvalue())
        self.assertIn("GBR", out.getvalue())

    def test_adopter_rows_isolate_the_law_and_take_a_true_median(self):
        med = {"medical_degrees", "pharmaceuticals", "modern_nursing", "antibiotics", "modern_vaccines"}

        def country(tag, laws=(), level=0, sol=12.0):
            c = S.CountryInputs(tag, population=1000.0, sol_x_size=sol * 1000, literate=400.0, workforce=1000.0,
                                incorporated_people=1000.0)
            c.techs, c.laws = set(med), set(laws)
            c.institutions = {"institution_health_system": level} if level else {}
            return c

        inputs = {"PHI": country("PHI", {"law_public_health_insurance"}, 4),
                  "AAA": country("AAA", sol=11.0), "BBB": country("BBB", sol=13.0)}
        rows = H.adopter_rows(inputs, H.DM.load_carriers())
        self.assertEqual(len(rows), 1)
        law, tag, _sol, _lit, inc, level, e0, own, median, n = rows[0]
        self.assertEqual((law, tag, level, n), ("law_public_health_insurance", "PHI", 4, 2))
        self.assertEqual(inc, 1.0)
        self.assertGreater(e0, own)                     # the law and its level add years
        peers = [H.life(H.inputs_for(inputs[t]))["e0"] for t in ("AAA", "BBB")]
        self.assertAlmostEqual(median, sum(peers) / 2)  # two peers: the mean of both, not the upper

    def test_buy_package_costs_rise_with_wealth(self):
        costs = H.buy_package_costs()
        self.assertEqual(len(costs), 200)
        self.assertLess(costs[1], costs[20])
        # uncapped up to the top level (2026-10-10, high wealth): the cap at 60 lumped late fortunes together
        self.assertEqual(H.income_proxy(150, costs), costs[150])
        self.assertEqual(H.income_proxy(250, costs), costs[200])
        self.assertEqual(H.income_proxy(0, costs), costs[1])

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

    def _step(self, pop=2_000_000, pop_after=2_010_000, war=500, kills=0, mig=-3000, logged_mmr=True):
        """(before, head, after) of one in-game step: the model stepped from its own seed.

        logged_mmr False steps the "after" ring with no maternal deaths while the head still logs
        the real rate, so the lines describe a script that skipped them.
        """
        inp = M.Inputs(sol=11, literacy=0.35, urban_share=0.3)
        before = M.seed(inp, 1836, pop)
        after = copy.deepcopy(before)
        qf, qm, mmr = M.group_rates(inp)
        mult = M.cause_multipliers(inp)
        work_f, work_m = M.work_split(inp, mult["work"])
        tfr = M.fertility(inp, 40)["tfr"]
        prof = M.migrant_profile(inp)
        M.step(after, inp, 1837, engine_pop=pop_after, war_dead=war, kills=kills, migration=mig,
               rates=(qf, qm, mmr if logged_mmr else 0.0, tfr, prof))
        head = {"pop": pop_after, "war": war, "kills": kills, "mig": mig, "tfr": tfr, "mmr": mmr,
                "m_inf": mult["infection"], "m_ext": mult["external"], "m_chr": mult["chronic"],
                "m_work_f": work_f, "m_work_m": work_m, "profile": prof}
        return before, head, after

    def _step_lines(self, pop=2_000_000, pop_after=2_010_000, war=500, mig=-3000, logged_mmr=True,
                    drop_after=False):
        """The 31 lines of one in-game step: the model stepped from its own seed.

        drop_after writes the after cohorts under half a person as 0, as the game drops them.
        """
        before, head, after = self._step(pop, pop_after, war, 0, mig, logged_mmr)
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
        # the panel's figure (wealth bands, no map) beside each pop as its own group and the old strata
        code, out, _err = self._cli("gini", str(SLICE), "--tag", "GBR")
        self.assertEqual(code, 0)
        self.assertNotIn("GINI_SCALE", out)
        m = re.search(r"^GBR\s+shown (\d\.\d+)\s+bands (\d\.\d+)\s+pop by pop (\d\.\d+)\s+strata (\d\.\d+)",
                      out, re.M)
        self.assertIsNotNone(m, out)
        shown, bands, pops, strata = (float(x) for x in m.groups())
        self.assertAlmostEqual(shown, 1 - 0.7 * (1 - bands), delta=0.001)   # both printed to 3 places
        self.assertGreater(bands, 0)
        self.assertLessEqual(bands, pops + 1e-9, "a coarser grouping never raises the Gini")
        self.assertLess(pops - bands, 0.05)
        self.assertLessEqual(strata, pops + 1e-9)

    @unittest.skipUnless(SLICE.exists(), "fixture written in Task 3")
    def test_gini_shift_moves_every_pop_up_the_wealth_levels(self):
        """--shift N: a synthetic late game, each pop N levels richer (capped at the top level)."""
        def figures(*extra):
            code, out, _err = self._cli("gini", str(SLICE), "--tag", "GBR", *extra)
            self.assertEqual(code, 0)
            m = re.search(r"^GBR\s+shown (\d\.\d+)\s+bands (\d\.\d+)\s+pop by pop (\d\.\d+)", out, re.M)
            self.assertIsNotNone(m, out)
            return [float(x) for x in m.groups()]
        self.assertEqual(figures("--shift", "0"), figures())
        _shown, bands, pops = figures("--shift", "45")
        self.assertLessEqual(bands, pops + 1e-9)
        self.assertLess(pops - bands, 0.05, "the bands still track pop by pop with most people above 50")

    @unittest.skipUnless(SLICE.exists(), "fixture written in Task 3")
    def test_gini_exits_1_when_a_tag_has_no_pops(self):
        code, out, err = self._cli("gini", str(SLICE), "--tag", "XXX")
        self.assertEqual(code, 1, out)
        self.assertIn("XXX", err)

    def test_save_commands_exit_1_on_a_non_plain_text_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "autosave.v3"
            path.write_bytes(b"SAV0103\n\xffU\x01\x00PK\x03\x04\x00\x00")
            for argv in (("gini", str(path)), ("seed", str(path), "--tag", "GBR"), ("inputs", str(path)),
                         ("natural-change", str(path), str(path)), ("history", str(path), "--anchors", str(ANCHORS))):
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


def _debug_logs(path, effect):
    """The debug_log strings of a top-level scripted effect, in order."""
    text = Path(path).read_text(encoding="utf-8-sig")
    m = re.search(rf"^{effect} = \{{", text, re.M)
    assert m, f"{effect} not in {path}"
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return re.findall(r'debug_log = "([^"]*)"', text[m.end():i])


def _render(template, resolve):
    """The line the game writes: each [..] template replaced by what resolve(inside) returns."""
    return re.sub(r"\[([^\]]*)\]", lambda m: resolve(m.group(1)), template)


def _game_number(x, places):
    """A value as the debug log prints it with |N: fixed decimals, or an integer for |0."""
    return f"{x:.{places}f}" if places else str(int(x))


class TestConsoleReplayLines(unittest.TestCase):
    """te_debug_demog.1 option a's lines, rendered from the script's own debug_log templates with a
    model step's numbers (as the game would print them), must parse, check and replay: a field
    renamed or dropped in te_debug_demog_effects.txt, or in the generated ring lines, fails here."""

    step = TestHarness._step

    @staticmethod
    def _heads():
        heads = _debug_logs(CONSOLE, "te_debug_demog_replay")
        assert len(heads) == 2, heads
        negative = [h for h in heads if " mig=-[" in h]
        other = [h for h in heads if " mig=[" in h]
        assert len(negative) == 1 and len(other) == 1, heads
        assert negative[0].replace(" mig=-[", " mig=[") == other[0], "the two heads differ beyond the sign"
        return negative[0], other[0]

    @staticmethod
    def _head_resolver(year, people, rates, profile):
        def resolve(inside):
            if inside == "THIS.ScriptValue('te_demog_year')|0":
                return str(year)
            m = re.fullmatch(r"THIS\.ScriptValue\('te_debug_demog_(\w+)_g([123])'\)\|0", inside)
            if m:   # the script values: abs, divide, floor, modulo
                n = int(abs(people[m.group(1)]))
                return str((n // 1_000_000, n // 1000 % 1000, n % 1000)[int(m.group(2)) - 1])
            m = re.fullmatch(r"THIS\.Var\('te_dg_dbg_(\w+)'\)\.GetValue\|(\d)", inside)
            if m and m.group(1) in rates:
                return _game_number(rates[m.group(1)], int(m.group(2)))
            m = re.fullmatch(r"THIS\.Var\('te_dg_dbg_p([fm])(\d)'\)\.GetValue\|(\d)", inside)
            if m:
                return _game_number(profile[(int(m.group(2)), m.group(1))], int(m.group(3)))
            raise AssertionError(f"head template the test can't read: [{inside}]")
        return resolve

    @staticmethod
    def _ring_resolver(ring):
        f, m, (pf, pm) = H._per_mille(ring)
        slots = {"f": f, "m": m}

        def resolve(inside):
            hit = re.fullmatch(r"THIS\.ScriptValue\('te_demog_dbg_([fm])(\d+)'\)\|(\d)", inside)
            if hit:
                return _game_number(slots[hit.group(1)][int(hit.group(2))], int(hit.group(3)))
            hit = re.fullmatch(r"THIS\.ScriptValue\('te_demog_dbg_pool_([fm])'\)\|(\d)", inside)
            if hit:
                return _game_number(pf if hit.group(1) == "f" else pm, int(hit.group(2)))
            hit = re.fullmatch(r"THIS\.Var\('te_dg_pa'\)\.GetValue\|(\d)", inside)
            if hit:
                return _game_number(ring.pool_age, int(hit.group(1)))
            raise AssertionError(f"ring template the test can't read: [{inside}]")
        return resolve

    def _console_lines(self, mig, kills):
        before, head, after = self.step(war=500, kills=kills, mig=mig)
        negative, other = self._heads()
        people = {"pop_last": before.people(), "pop": head["pop"], "war": head["war"], "kills": head["kills"],
                  "mig": head["mig"]}
        rates = {k: head[k] for k in H.HEAD_RATES}
        head_line = _render(negative if mig < 0 else other,
                            self._head_resolver(1837, people, rates, head["profile"]))
        lines = [head_line]
        for when, ring in (("before", before), ("after", after)):
            templates = _debug_logs(GENERATED_EFFECTS, f"te_demog_debug_log_ring_{when}")
            lines += [_render(t, self._ring_resolver(ring)) for t in templates]
        return [LOG_PREFIX + x for x in lines]

    def test_the_consoles_lines_replay(self):
        for mig, kills in ((-3000, 0), (4000, 250)):
            with self.subTest(mig=mig):
                lines = self._console_lines(mig, kills)
                self.assertEqual(len(lines), 31)
                self.assertFalse([x for x in lines if "[" in x[len(LOG_PREFIX):]], "an unresolved template")
                blocks = H.parse_replay(lines)
                self.assertEqual(len(blocks), 1)
                block = blocks[0]
                self.assertEqual(block["head"]["state"], "capital")
                self.assertEqual(set(block["head"]), {"state", "year", *H.HEAD_PEOPLE, *H.HEAD_RATES, "profile"})
                self.assertEqual(H._ungroup(block["head"]["mig"]), mig)
                self.assertEqual(H._ungroup(block["head"]["kills"]), kills)
                self.assertIsNone(H.check_block(block))
                self.assertLess(H.replay_block(block), H.DEFAULT_TOLERANCE)

    def test_the_cli_reads_the_consoles_lines(self):
        lines = self._console_lines(-3000, 0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "debug.log"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = H.main(["replay", str(path)])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("capital 1837: worst slot error", out.getvalue())


# A plain-text save cut to what `wc` reads. Country 1's record holds a nested database that
# restarts at column 0, as the game writes it; its variables include a negative (unsigned i64).
WC_SAVE = """SAV0100wc-test
meta_data={
\tversion="1.14.5"
}
country_manager={
\tdatabase={
0=none
1={
\tdefinition="GBR"
\tbudget={
0={
\tvalue=3
}
\t}
\tvariables={
\t\tdata={ {
\t\t\t\tflag=te_inh_concentration
\t\t\t\tdata={
\t\t\t\t\ttype=value
\t\t\t\t\tidentity=7632845
\t\t\t\t}
\t\t\t} {
\t\t\t\tflag=te_dg_wc_t_own
\t\t\t\tdata={
\t\t\t\t\ttype=value
\t\t\t\t\tidentity=18446744073708401616
\t\t\t\t}
\t\t\t} {
\t\t\t\tflag=te_unrelated
\t\t\t\tdata={
\t\t\t\t\ttype=value
\t\t\t\t\tidentity=100000
\t\t\t\t}
\t\t\t} }
\t}
}
2={
\tdefinition="SIC"
}
\t}
}
states={
\tdatabase={
5={
\tcountry=1
\tvariables={
\t\tdata={ {
\t\t\t\tflag=te_dg_wc
\t\t\t\tdata={
\t\t\t\t\ttype=value
\t\t\t\t\tidentity=9400000
\t\t\t\t}
\t\t\t} {
\t\t\t\tflag=te_dg_walk_pop
\t\t\t\tdata={
\t\t\t\t\ttype=value
\t\t\t\t\tidentity=200000000000
\t\t\t\t}
\t\t\t} }
\t}
}
6={
\tcountry=1
\tvariables={
\t\tdata={ {
\t\t\t\tflag=te_dg_wc
\t\t\t\tdata={
\t\t\t\t\ttype=value
\t\t\t\t\tidentity=4000000
\t\t\t\t}
\t\t\t} }
\t}
}
\t}
}
laws={
\tdatabase={
10={
\tlaw=law_primogeniture
\tcountry=1
\tactive=yes
}
11={
\tlaw=law_partible
\tcountry=1
}
\t}
}
"""


class TestWealthConcentrationReader(unittest.TestCase):
    """`wc`: the national figure, its terms and the states' scores read from script variables."""

    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "wc.v3"
        self.path.write_text(WC_SAVE, encoding="utf-8")

    def test_variables_decode_as_fixed_point_and_wrap_negative(self):
        self.assertEqual(S.fixed_point("7632845"), 76.32845)
        self.assertEqual(S.fixed_point(str(2 ** 64 - 1150000)), -11.5)

    def test_the_reader_finds_country_and_state_variables(self):
        countries, states = S.read_variables(self.path, H.WC_COUNTRY_VARS, H.WC_STATE_VARS)
        self.assertEqual(countries["1"]["tag"], "GBR")
        self.assertEqual(countries["1"]["vars"], {"te_inh_concentration": 76.32845, "te_dg_wc_t_own": -11.5})
        self.assertEqual(countries["1"]["laws"], {"law_primogeniture"}, "only the active law")
        self.assertEqual(countries["2"]["vars"], {})
        self.assertEqual(states["5"], {"owner": "1", "vars": {"te_dg_wc": 94.0, "te_dg_walk_pop": 2e6}})
        self.assertEqual(states["6"]["vars"], {"te_dg_wc": 40.0})

    def test_the_cli_prints_each_country_and_the_laws_summary(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["wc", str(self.path)]), 0)
        text = out.getvalue()
        self.assertRegex(text, r"GBR\s+2\.0\s+76\.3")
        self.assertIn("1/2", text, "one of the two states above 50")
        self.assertIn("40-94", text)
        self.assertNotIn("SIC", text, "no national figure: left out")
        self.assertRegex(text, r"primogeniture\s+countries\s+1\s+above 50\s+1")

    def test_wc_exits_1_on_a_non_plain_text_save(self):
        bad = self.path.with_name("binary.v3")
        bad.write_bytes(b"SAV010000\x00\x01binary")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(H.main(["wc", str(bad)]), 1)


class TestFidelity(unittest.TestCase):
    """`fidelity SAVE`: the model's cause multipliers on the census's own SoL and literacy (te_dg_sol, te_dg_lit)
    against the ones the census stored (te_dg_m_*). A term the harness can't read shows as a mismatch: the
    crowding term did, on 91% of the world's people (2026-10-10)."""

    CROWD_MULT = 1.5   # the crowded state's migration_crowding multiplier: a -15% pull, so infection x1.15
    GAME_SOL, GAME_LIT = 8.0, 0.2   # the walk's figures; the tiny save's pops read SoL 28, literacy 0.5

    def setUp(self):
        from test_demographics_save_inputs import TINY
        self.tiny = TINY
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        for p in self.tmp.iterdir():
            p.unlink()
        self.tmp.rmdir()

    def game_multipliers(self, poverty_floor=None):
        """The census's stored multipliers for state 1 in game, where it carries migration_crowding: infection,
        and maternal as deaths per 100,000 births. poverty_floor: the build's poverty term, if not this branch's."""
        st = S.state_inputs(S.read_sections(self.save(False, 1.0)))["TST"][0][1]
        inp = H.inputs_for(st, DM.load_carriers())
        kept = H.P.POVERTY_INFECTION_AT_FLOOR
        if poverty_floor is not None:
            H.P.POVERTY_INFECTION_AT_FLOOR = poverty_floor
        try:
            mult = M.cause_multipliers(M.Inputs(sol=self.GAME_SOL, literacy=self.GAME_LIT,
                                                institutions=inp.institutions, mods=inp.mods))
        finally:
            H.P.POVERTY_INFECTION_AT_FLOOR = kept
        crowding = 1 + H.P.MIGRATION_CROWDING_PULL_PER_MULT * self.CROWD_MULT
        return mult["infection"] * crowding, mult["maternal"] * H.P.MATERNAL_PER_100K_BIRTHS

    def game_infection(self, poverty_floor=None):
        return self.game_multipliers(poverty_floor)[0]

    def save(self, crowded, m_inf, m_mat=None):
        def var(name, value):
            return (f"\t\t\t\tflag={name}\n\t\t\t\tdata={{\n\t\t\t\t\ttype=value\n"
                    f"\t\t\t\t\tidentity={round(value * 1e5)}\n\t\t\t\t}}\n")
        block = "\tvariables={\n\t\tdata={ {\n" + "\t\t\t} {\n".join(
            var(n, v) for n, v in (("te_dg_sol", self.GAME_SOL), ("te_dg_lit", self.GAME_LIT), ("te_dg_m_inf", m_inf),
                                   ("te_dg_m_mat", m_mat)) if v is not None
        ) + "\t\t\t} }\n\t}\n"
        if crowded:
            block += ("\ttimed_modifiers={\n\t\tmodifiers={ {\n\t\t\t\tid=5\n\t\t\t\tmodifier=migration_crowding\n"
                      f"\t\t\t\tmultiplier={self.CROWD_MULT}\n\t\t\t}} }}\n\t}}\n")
        state = "1={\n\tcountry=3\n\tincorporation=1\n"
        text = self.tiny.replace(state + "}", state + block + "}", 1)
        self.assertNotEqual(text, self.tiny)
        path = self.tmp / f"s{int(crowded)}_{m_inf:.5f}.v3"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_a_crowded_state_matches(self):
        rows = H.fidelity_rows(self.save(True, *self.game_multipliers()), DM.load_carriers())
        (_tag, sid, _people, pairs, _sol, _lit), = rows
        self.assertEqual(sid, "1")
        for cause in ("infection", "maternal"):   # maternal is stored per 100,000 births
            game, model = pairs[cause]
            self.assertAlmostEqual(game / model, 1.0, places=4, msg=cause)

    def test_a_save_from_another_build_takes_its_poverty_floor(self):
        # a save from main (no poverty term) reads as off everywhere below SoL 9 unless fidelity is told (review I2)
        path = self.save(True, self.game_infection(poverty_floor=1.0))
        kept = H.P.POVERTY_INFECTION_AT_FLOOR
        for argv, code in ((["fidelity", path], 1), (["fidelity", path, "--poverty-floor", "1"], 0)):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(H.main(argv), code, out.getvalue() + err.getvalue())
            self.assertEqual(H.P.POVERTY_INFECTION_AT_FLOOR, kept, "the branch's own value comes back")
        self.assertIn("poverty", out.getvalue())

    def test_an_unknown_tag_is_named(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(H.main(["fidelity", self.save(True, self.game_infection()), "--tag", "XXX"]), 1)
        self.assertIn("XXX", err.getvalue())

    def test_a_term_the_harness_cant_see_shows(self):
        # the same stored multiplier, but the save no longer shows the modifier the census applied
        rows = H.fidelity_rows(self.save(False, self.game_infection()), DM.load_carriers())
        game, model = rows[0][3]["infection"]
        self.assertAlmostEqual(game / model, 1.15, places=3)

    def test_the_save_readers_sol_beside_the_walks(self):
        rows = H.fidelity_rows(self.save(True, self.game_infection()), DM.load_carriers())
        self.assertEqual(rows[0][4], (28.0, self.GAME_SOL))
        self.assertEqual(rows[0][5], (0.5, self.GAME_LIT))

    def test_cli_exits_1_on_a_mismatch(self):
        for crowded, code in ((True, 0), (False, 1)):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                got = H.main(["fidelity", self.save(crowded, self.game_infection())])
            self.assertEqual(got, code, out.getvalue() + err.getvalue())
            self.assertIn("infection", out.getvalue())

    def test_cli_says_when_no_state_was_walked(self):
        path = self.tmp / "plain.v3"
        path.write_text(self.tiny, encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(H.main(["fidelity", str(path)]), 1)
        self.assertIn("te_dg_m_inf", err.getvalue())
