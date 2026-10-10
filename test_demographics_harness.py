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
        self.assertRegex(line, r"people \+0\.8\d%")       # 1820-1850, the benchmarks around 1836
        self.assertRegex(out, r"world .* e0 \d+\.\d")

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
