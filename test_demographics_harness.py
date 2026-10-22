"""scripts/analysis/demographics_harness.py: the sketch, the Gini anchor and the replay round trip."""

import copy
import dataclasses
import io
import json
import math
import re
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_harness as H  # noqa: E402
import demographics_model as M  # noqa: E402
import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_save_inputs as S  # noqa: E402

SLICE = ROOT / "test_fixtures" / "demographics" / "gb_1836_slice.v3"
ANCHORS = ROOT / "test_fixtures" / "demographics" / "history_anchors.csv"
CONSOLE = ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"
GENERATED_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_generated_effects.txt"
LOG_PREFIX = "[12:00:00][jomini_effect_impl.cpp:454]: common/scripted_effects/te_debug_demog_effects.txt:66: "


class TestPredict(unittest.TestCase):
    D = H.G.read_defines()

    def test_a_fed_state_runs_at_the_census_rates_plus_nothing(self):
        out = H.predict_state([H.Pop(1e6, 9.0, 0.0, 0.8)], cbr=40.0, cdr=30.0, d=self.D)
        self.assertAlmostEqual(out["births"] / 1e3, 40.0, places=6)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0, places=6)

    def test_literacy_is_netted(self):
        out = H.predict_state([H.Pop(1e6, 9.0, 0.5, 0.8)], cbr=40.0, cdr=30.0, d=self.D)
        self.assertAlmostEqual(out["births"] / 1e3, 40.0, places=6)

    def test_terms_on_top(self):
        """Severe starvation (births -0.9, deaths +1.0, x the pop's starvation value: 0.75 at food security 0.1, the
        famine probe) is a pop's own line, at the bare curve's weight; devastation's 0.2 and a law's -0.1 births are
        state-level, and act on the census's rate (owner, 2026-10-11)."""
        out = H.predict_state([H.Pop(1e6, 9.0, 0.0, 0.1)], cbr=40.0, cdr=30.0, d=self.D, on_top_b=-0.1, on_top_d=0.2)
        bare_b = 1e6 * H.G.monthly_birthrate(9.0, self.D) * 12
        bare_d = 1e6 * H.G.monthly_mortality(9.0, self.D) * 12
        sv = (0.4 - 0.1) * 2.5
        self.assertAlmostEqual(out["deaths"], 30.0 * 1e3 * 1.2 + bare_d * 1.0 * sv, delta=1.0)
        self.assertAlmostEqual(out["births"], max(0.0, 40.0 * 1e3 * 0.9 - bare_b * 0.9 * sv), delta=1.0)

    def test_pollution_mortality(self):
        """Pollution Impact's mortality line at a region's pollution: half the maximum gives half the line."""
        self.assertAlmostEqual(H.pollution_mortality(H.P.POLLUTION_MAX / 2), H.P.POLLUTION_HEALTH_MORTALITY / 2)
        self.assertEqual(H.pollution_mortality(0.0), 0.0)

    def test_predict_save_adds_pollution_to_deaths_only(self):
        """predict_save passes each state its region's Pollution Impact line among the deaths on top, never births."""
        from test_demographics_save_inputs import TINY
        text = TINY.replace("\tcountry=3\n\tincorporation=1\n}", "\tcountry=3\n\tincorporation=1\n\tregion=\"STATE_TEST\"\n}", 1)
        self.assertIn('region="STATE_TEST"', text)
        seen = []
        real = H.predict_state

        def spy(pops, cbr, cdr, d, **kw):
            seen.append(kw)
            return real(pops, cbr, cdr, d, **kw)

        line_carriers = H.DM.line_carriers()
        with tempfile.TemporaryDirectory() as tmp:
            for pollution, path in ((127.5, Path(tmp) / "polluted.v3"), (0.0, Path(tmp) / "clean.v3")):
                path.write_text(text.replace("pollution=127.5", f"pollution={pollution}"), encoding="utf-8")
                H.predict_state = spy
                try:
                    H.predict_save(str(path), line_carriers, H.DM.load_carriers(), self.D)
                finally:
                    H.predict_state = real
        polluted, clean = seen
        self.assertAlmostEqual(polluted["on_top_d"] - clean["on_top_d"], H.pollution_mortality(127.5))
        self.assertEqual(polluted["on_top_b"], clean["on_top_b"])

    def test_state_level_terms_on_top_act_on_the_census_rate(self):
        out = H.predict_state([H.Pop(1e6, 9.0, 0.0, 0.8)], cbr=40.0, cdr=30.0, d=self.D, on_top_d=0.32)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0 * 1.32, places=6)
        self.assertAlmostEqual(out["births"] / 1e3, 40.0, places=6)

    def test_the_slope_is_reported_not_applied(self):
        pops = [H.Pop(1e6, 1.0, 0.0, 0.8)]
        out = H.predict_state(pops, 40.0, 30.0, self.D)
        slope = 1e6 * (H.G.monthly_mortality(1.0, self.D) - H.G.monthly_mortality(4.0, self.D)) * 12
        self.assertAlmostEqual(out["slope_deaths"], slope, delta=1.0)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0, places=6)

    def test_absorbed_class_lines_are_reported_not_applied(self):
        """Owner, 2026-10-11 (the engine-lines plan): child labour's class line is script-only, so under Full the engine
        doesn't apply it; predict reports what it would have done on top."""
        pops = [H.Pop(1e6, 9.0, 0.0, 0.8, on_top_d=0.0, absorbed_d=0.05)]
        out = H.predict_state(pops, 40.0, 30.0, self.D)
        self.assertAlmostEqual(out["absorbed_child_labour_deaths"],
                               1e6 * H.G.monthly_mortality(9.0, self.D) * 12 * 0.05, delta=1.0)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0, places=6)

    def test_absorbed_state_lines_are_reported_not_applied(self):
        """The absorbed family's lines (a health law at level 3, No Women's Rights) don't reach the engine under Full: the
        events are the census's. Each report group gets its own share, at the bare curves."""
        out = H.predict_state([H.Pop(1e6, 9.0, 0.0, 0.8)], 40.0, 30.0, self.D,
                              groups={"womens_rights": (0.05, 0.0), "health": (0.0, -0.15)})
        self.assertAlmostEqual(out["births"] / 1e3, 40.0, places=6)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0, places=6)
        self.assertAlmostEqual(out["absorbed_womens_rights_births"],
                               1e6 * H.G.monthly_birthrate(9.0, self.D) * 12 * 0.05, delta=1.0)
        self.assertAlmostEqual(out["absorbed_health_deaths"],
                               1e6 * H.G.monthly_mortality(9.0, self.D) * 12 * -0.15, delta=1.0)
        self.assertEqual(out["absorbed_other_lines_births"], 0.0)

    def test_the_on_top_family_applies_at_the_census_rate(self):
        out = H.predict_state([H.Pop(1e6, 9.0, 0.0, 0.8)], 40.0, 30.0, self.D, added_b=0.10, added_d=-0.05)
        self.assertAlmostEqual(out["births"] / 1e3, 40.0 * 1.10, places=6)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0 * 0.95, places=6)

    def test_the_wealth_line_is_floored_and_scaled(self):
        """Owner, 2026-10-11 (option b): Private Health Insurance's wealth line at the census's rate, at least
        P.WEALTH_LINE_FLOOR a wealth level, so a wealth-99 pop dies at no less than half the census's rate."""
        rich = H.Pop(1e6, 30.0, 0.0, 0.8, wealth=99)
        out = H.predict_state([rich], 40.0, 30.0, self.D, wealth=-0.01)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0 * (1 + 99 * H.P.WEALTH_LINE_FLOOR), places=4)
        poor = H.Pop(1e6, 30.0, 0.0, 0.8, wealth=10)
        out = H.predict_state([poor], 40.0, 30.0, self.D, wealth=-0.002)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0 * (1 - 0.002 * 10), places=4)

    def test_mild_starvation_is_absorbed_and_severe_stays_on_top(self):
        """Owner amendment B: mild starvation's terms are netted by M, severe starvation's still apply."""
        bare_b = 1e6 * H.G.monthly_birthrate(9.0, self.D) * 12
        bare_d = 1e6 * H.G.monthly_mortality(9.0, self.D) * 12
        out = H.predict_state([H.Pop(1e6, 9.0, 0.0, 0.3)], 40.0, 30.0, self.D)
        self.assertAlmostEqual(out["births"] / 1e3, 40.0, places=6)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0, places=6)
        sb, sd = M.starvation_terms(0.3)
        self.assertAlmostEqual(out["absorbed_mild_births"], bare_b * sb, delta=1.0)
        self.assertAlmostEqual(out["absorbed_mild_deaths"], bare_d * sd, delta=1.0)
        out = H.predict_state([H.Pop(1e6, 9.0, 0.0, 0.1)], 40.0, 30.0, self.D)
        self.assertAlmostEqual(out["deaths"], 30.0 * 1e3 + bare_d * 1.0 * 0.75, delta=1.0)   # x its starvation value
        self.assertEqual(out["absorbed_mild_deaths"], 0.0)

    def test_the_clamp_sees_the_lines_left_in_the_read(self):
        """The script's 'other' is the state read without the census's, fast mode's and the moved lines' terms: the
        engine's state lines left on top, as predict's on_top."""
        # mild hunger's deaths (absorbed) above a census rate of 2 per 1,000 under a -0.5 line: the read stops at -1
        out = H.predict_state([H.Pop(1e6, 9.0, 0.0, 0.3)], 40.0, 2.0, self.D, on_top_d=-0.5)
        self.assertTrue(out["clamped"])
        self.assertAlmostEqual(out["m_d"], H.P.RATE_TOTAL_FLOOR + 0.5)
        # a line past the engine's floor in the read: the census adds nothing more
        out = H.predict_state([H.Pop(1e6, 9.0, 0.0, 0.3)], 40.0, 2.0, self.D, on_top_d=-1.2)
        self.assertTrue(out["clamped"])
        self.assertEqual(out["m_d"], 0.0)

    def test_predict_on_the_slice(self):
        """The command end to end on the test slice (Britain and Portugal, 1836; the slice has no game_date)."""
        out = io.StringIO()
        with redirect_stdout(out):
            code = H.main(["predict", str(SLICE), "--year", "1836", "--json"])
        data = json.loads(out.getvalue())
        world = data["saves"][SLICE.name]["world"]
        self.assertGreater(world["people"], 0)
        self.assertGreater(world["child_labour_points"], 0)     # both hold Child Labor Allowed
        self.assertLess(world["womens_rights_points"], 0)       # Portugal's No Women's Rights (Britain: Own Property)
        for k in ("health_points", "other_lines_points", "mild_starvation_points"):
            self.assertIn(k, world)
        # the slice's pops carry no food security (fed) and their laws no line on top: the engine runs the census
        self.assertAlmostEqual(world["growth"], world["census_growth"], places=6)
        self.assertEqual(code, 0 if data["in_band"] and not data["saves"][SLICE.name]["shrinking"] else 1)

    def test_multiple_chains_the_saves_rates(self):
        # 1% a year from 1837 to 1887, then 0.5% to 1900
        self.assertAlmostEqual(H.predicted_multiple([(1837, 1.0), (1887, 0.5)], 1900),
                               math.exp(0.01 * 50 + 0.005 * 13), places=9)


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

    def test_augmentation_reaches_only_as_far_as_access(self):
        """Phase 2 step 4 (owner: it doesn't help you that artificial hearts exist if you don't have access to them):
        augmentation's chronic treatment acts through health-care access, so with no health system (access at its
        base) Unrestricted Augmentation gives less than that base's share of what it gives Rich today (access 1).
        Its old flat -5% mortality reached every state alike."""
        rows = dict(H.medicine_rows())
        poor = rows["Unrestricted Augmentation, no health system"]["gap"][0]
        rich = rows["Unrestricted Augmentation, Rich today"]["gap"][0]
        self.assertGreater(poor, 0)
        self.assertLess(poor, H.P.BASE_ACCESS * rich)

    def test_no_womens_rights_leaves_the_reference_alone(self):
        rows = {r[0]: r[1] for r in H.fertility_rows()}
        self.assertAlmostEqual(rows["1836 agrarian, No Women's Rights"], rows["1836 agrarian (reference)"], places=9)

    def test_fertility_anchors_hold(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["fertility"]), 0, out.getvalue())
        for label, _kw, _band in H.FERTILITY_SCENARIOS:
            self.assertIn(label, out.getvalue())
        self.assertNotIn(" OUT", out.getvalue())

    def test_the_practice_scenarios(self):
        """Spec 5.1 item 4's shares on every fertility scenario, and review I3's two: the 20th century where Birth
        Spacing has eroded and the raise is all that's left."""
        labels = [label for label, _kw, _band in H.PRACTICE_SCENARIOS]
        self.assertIs(H.FERTILITY_SCENARIOS, H.PRACTICE_SCENARIOS, "Task 6: the fertility command judges the shares")
        self.assertEqual(len(labels), len(H._SCENARIO_PRACTICES) + 2)
        self.assertIn("East Asia 1990", labels)
        self.assertIn("Latin America 1970", labels)
        rows = dict((r[0], r[1]) for r in H.fertility_rows(scenarios=H.PRACTICE_SCENARIOS))
        self.assertAlmostEqual(rows["1836 agrarian, No Women's Rights"], rows["1836 agrarian (reference)"], places=9)

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

    @unittest.skipUnless(SLICE.exists(), "fixture written in Task 3")
    def test_history_reads_a_saves_own_shares_under_a_replays(self):
        """Stop B, M2: each state's shares are its seed, then the save's own (te_dg_pr_*, `saved`), then a replay's
        (`shares`, the --shares file), each overriding the one before."""
        sections = S.read_sections(SLICE)
        gbr = [sid for sid, _st, _inc in S.state_inputs(sections)["GBR"]]
        def tfr(**kw):
            rows, _world, _bare = H.history_rows(sections, 1836, {}, **kw)
            return next(r[3]["tfr"] for r in rows if r[1] == "GBR")
        seeded = tfr()
        saved = tfr(saved={sid: {"lm": 1.0, "bs": 0.0} for sid in gbr})
        self.assertAlmostEqual(saved, seeded * (1 - P.PRACTICE_CUT["lm"]), places=6)
        self.assertAlmostEqual(tfr(saved={sid: {"lm": 1.0, "bs": 0.0} for sid in gbr},
                                   shares={sid: {"lm": 0.0, "bs": 0.0} for sid in gbr}), seeded, places=6)

    def test_history_takes_each_states_practices(self):
        """The late-marriage plan, Task 3: a state's shares multiply its children per woman, and a country's figure
        can leave its colonies out (spec 5.1 item 3: Denmark's West African states)."""
        carriers = DM.load_carriers()

        def state(people):
            c = S.CountryInputs("TST")
            c.population, c.sol_x_size, c.wealth_tfr_x_size = people, 8.0 * people, M.wealth_tfr(8.0) * people
            c.workforce, c.literate = people / 2, people / 10
            return c

        states = [("1", state(1000.0), True), ("2", state(1000.0), False)]
        plain = H.country_figures(states, carriers)
        late = H.country_figures(states, carriers, shares={"1": {"lm": 1.0}, "2": {"lm": 1.0}})
        self.assertAlmostEqual(late["tfr"], plain["tfr"] * (1 - P.PRACTICE_CUT["lm"]), places=6)
        home = H.country_figures(states, carriers, shares={"1": {"lm": 1.0}}, incorporated_only=True)
        self.assertAlmostEqual(home["tfr"], H.model_figures(H.inputs_for(states[0][1], carriers,
                                                                         practices={"lm": 1.0}))["tfr"], places=6)

    def test_history_sees_the_censuss_lag(self):
        """A state whose stored medicine is behind its targets reads a lower life expectancy than at its targets; with
        nothing stored, the figures are as before (the Causes of Death plan, Task 10)."""
        carriers = DM.load_carriers()
        c = S.CountryInputs("TST")
        c.population, c.sol_x_size, c.wealth_tfr_x_size = 1000.0, 13.0 * 1000.0, M.wealth_tfr(13.0) * 1000.0
        c.workforce, c.literate = 500.0, 100.0
        c.techs = {"medical_degrees", "pharmaceuticals", "modern_nursing"}
        states = [("1", c, True)]
        at_target = H.country_figures(states, carriers)
        behind = {"1": dict(TestFidelity.STORED, te_dg_acc=0.4, te_dg_trt_inf=0.0, te_dg_trt_mat=0.0,
                            te_dg_trt_chr=0.0)}
        self.assertLess(H.country_figures(states, carriers, stored=behind)["e0"], at_target["e0"])
        self.assertEqual(H.country_figures(states, carriers, stored={}), at_target)

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
                "m_work_f": work_f, "m_work_m": work_m, "inf_ad": M.infection_adult(inp), "profile": prof}
        lines = H.format_replay("TEST", 1837, before, head, after)
        self.assertEqual(len(lines), 31)
        self.assertIn("pop=2_10_0", lines[0])
        blocks = H.parse_replay(lines)
        self.assertEqual(len(blocks), 1)
        self.assertLess(H.replay_block(blocks[0]), 0.001)

    def test_replay_reads_the_adults_infection_factor(self):
        """#1045: a state with medicine logs its adults' infection factor, and a replay that took it as 1 is off. A poor
        state half reached by medicine, where the factor moves the most deaths in a year (a few per thousand at 45-64)."""
        inp = M.Inputs(sol=5, literacy=0.0, urban_share=0.1,
                       mods={P.ACCESS_TYPE: 0.625 - P.BASE_ACCESS, P.TREATMENT_TYPE["infection"]: 0.8})
        self.assertAlmostEqual(M.infection_adult(inp), 0.6)
        before = M.seed(inp, 1836, 2_000_000)
        after = copy.deepcopy(before)
        qf, qm, mmr = M.group_rates(inp)
        mult = M.cause_multipliers(inp)
        work_f, work_m = M.work_split(inp, mult["work"])
        tfr = M.fertility(inp, 40)["tfr"]
        prof = M.migrant_profile(inp)
        M.step(after, inp, 1837, engine_pop=2_000_000, rates=(qf, qm, mmr, tfr, prof))
        head = {"pop": 2_000_000, "war": 0, "kills": 0, "mig": 0, "tfr": tfr, "mmr": mmr,
                "m_inf": mult["infection"], "m_ext": mult["external"], "m_chr": mult["chronic"],
                "m_work_f": work_f, "m_work_m": work_m, "inf_ad": M.infection_adult(inp), "profile": prof}
        self.assertLess(H.replay_block(H.parse_replay(H.format_replay("TEST", 1837, before, head, after))[0]), 0.001)
        head["inf_ad"] = 1.0
        self.assertGreater(H.replay_block(H.parse_replay(H.format_replay("TEST", 1837, before, head, after))[0]),
                           H.DEFAULT_TOLERANCE)

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
                "m_work_f": work_f, "m_work_m": work_m, "inf_ad": M.infection_adult(inp), "profile": M.migrant_profile(inp)}
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
                "m_work_f": work_f, "m_work_m": work_m, "inf_ad": M.infection_adult(inp), "profile": prof}
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


def _variables(values):
    """A save's variables block: a number as a fixed-point value, ("state", id) as a state reference (the form
    a plain-text save writes, e.g. te_dg_primate_state in puerto rico_1836_01_20.v3)."""
    out = []
    for flag, v in values.items():
        if isinstance(v, tuple):
            kind, identity = v
        else:
            kind, identity = "value", round(v * 100000) % 2 ** 64
        out.append(f"\t\t\t\tflag={flag}\n\t\t\t\tdata={{\n\t\t\t\t\ttype={kind}\n\t\t\t\t\tidentity={identity}\n"
                   f"\t\t\t\t}}\n")
    return "\tvariables={\n\t\tdata={ {\n" + "\t\t\t} {\n".join(out) + "\t\t\t} }\n\t}\n"


def _effects_save(countries, states):
    """A plain-text save from {id: (tag, {var: value})} and {id: (owner id, {var: value})}."""
    text = "SAV0100effects-test\nmeta_data={\n\tversion=\"1.14.5\"\n}\ncountry_manager={\n\tdatabase={\n"
    for cid, (tag, values) in countries.items():
        text += f"{cid}={{\n\tdefinition=\"{tag}\"\n" + (_variables(values) if values else "") + "}\n"
    text += "\t}\n}\nstates={\n\tdatabase={\n"
    for sid, (owner, values) in states.items():
        text += f"{sid}={{\n\tcountry={owner}\n" + (_variables(values) if values else "") + "}\n"
    return text + "\t}\n}\n"


EFFECTS_COUNTRIES = {"1": ("GBR", {"te_inh_concentration": 76.3, "te_dg_primacy": 0.6, "te_dg_up_states": 3,
                                   "te_dg_primate_state": ("state", 5)}),
                     "2": ("SIC", {})}
EFFECTS_STATES = {"5": ("1", {"te_dg_wc": 94, "te_dg_walk_pop": 2e6, "te_dg_gini": 0.75, "te_dg_mt": 80,
                              "te_dg_sex_balance": 140, "te_dg_agr_share": 0.5}),
                  "6": ("1", {"te_dg_wc": 15, "te_dg_walk_pop": 1e6, "te_dg_gini": 0.5, "te_dg_mt": 10,
                              "te_dg_sex_balance": 75})}


def run(argv, code=0):
    """H.main(argv)'s printed text; it must return code."""
    out = io.StringIO()
    with redirect_stdout(out), redirect_stderr(io.StringIO()):
        got = H.main(argv)
    assert got == code, (argv, got, out.getvalue())
    return out.getvalue()


class TestEffects(unittest.TestCase):
    """Phase 0's readouts (2026-10-22 effects design): each condition's strength in a save, old curve against new."""

    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "effects.v3"
        self.path.write_text(_effects_save(EFFECTS_COUNTRIES, EFFECTS_STATES), encoding="utf-8")

    def test_raw_variables_keep_the_reference(self):
        countries, _ = S.read_variables(self.path, ("te_dg_primate_state", "te_dg_primacy"), (),
                                        raw=("te_dg_primate_state",))
        self.assertEqual(countries["1"]["vars"]["te_dg_primate_state"], "5")
        self.assertAlmostEqual(countries["1"]["vars"]["te_dg_primacy"], 0.6)

    def test_strength_bins(self):
        rows = H.strength_bins([(0.0, 1e6), (0.3, 2e6), (1.2, 1e6), (2.0, 5e5)])
        self.assertEqual([r[0] for r in rows], ["0", "0-0.5", "0.5-1", "1-1.5", "1.5-2", ">2"])
        self.assertEqual([r[1] for r in rows], [1, 1, 0, 1, 1, 0])
        self.assertEqual(rows[1][2], 2e6)

    def test_wc_prints_both_curves(self):
        text = run(["wc", str(self.path)])
        self.assertRegex(text, r"state scores.*\n.*80-90")
        self.assertIn("1-1.5", text)

    def test_gini_counts_states_above_070(self):
        # The fixture has no pops, so the pop-by-pop part reports none and exits 1; the census line still prints.
        self.assertRegex(run(["gini", str(self.path)], code=1), r"above 0\.70: 1 of 2 states \(67% of people\)")

    def test_effects_prints_every_condition(self):
        text = run(["effects", str(self.path)])
        for name in ("wc_high", "wc_low", "primacy", "metro_up", "inequality", "more_men", "fewer_men", "youth"):
            self.assertIn(name, text)
        self.assertIn("radicals stack", text)
        self.assertIn("turmoil stack", text)
        self.assertIn("primate Urban Center stack", text)

    def test_effects_reads_the_new_sizes(self):
        rows = H.effects_rows(*S.read_variables(self.path, H.EFFECT_COUNTRY_VARS, H.EFFECT_STATE_VARS,
                                                raw=H.EFFECT_RAW_VARS), {}, {})
        # The primate state 5: Primate City 0.2 x primacy(0.6) + Metropolis 0.1 x metro_up(80).
        self.assertEqual([r[0] for r in rows["uc"]], ["GBR"])
        self.assertAlmostEqual(rows["uc"][0][2], 0.2 * 1.2 + 0.1 * 1.5)
        radicals = dict((r[0], r[2]) for r in rows["radicals"])
        # State 5: Land Hunger 0.1 x wc_high(94) x 0.5 + Inequality 0.1 x inequality(0.75) + More Men 0.15 x
        # more_men(140); state 6: Dispersed Property -0.1 x wc_low(15) + Inequality 0.1 x inequality(0.5).
        self.assertAlmostEqual(radicals["5"], 0.1 * (44 / 30) * 0.5 + 0.1 * 1.75 + 0.15 * 1.25)
        self.assertAlmostEqual(radicals["6"], -0.1 * (1 + (35 / 30 - 1) / 2) + 0.1 * 0.25)
        turmoil = dict((r[0], r[2]) for r in rows["turmoil"])
        self.assertAlmostEqual(turmoil["6"], 0.15 * 1.2, msg="Provincial Neglect on the non-primate state")

    def test_effects_skips_missing_figures(self):
        states = dict(EFFECTS_STATES, **{"6": ("1", {"te_dg_wc": 15})})
        sparse = self.path.with_name("sparse.v3")
        sparse.write_text(_effects_save(EFFECTS_COUNTRIES, states), encoding="utf-8")
        text = run(["effects", str(sparse)])
        self.assertIn("wc_high", text)
        self.assertIn("inequality", text)


class TestFidelity(unittest.TestCase):
    """`fidelity SAVE`: the model's cause multipliers on the census's own SoL and literacy (the step's te_dg_in_sol
    and te_dg_in_lit, or the walk's te_dg_sol and te_dg_lit for a census from before them) against the ones the
    census stored (te_dg_m_*). A term the harness can't read shows as a mismatch: the crowding term did, on 91% of
    the world's people (2026-10-10)."""

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

    def save(self, crowded, m_inf, m_mat=None, extra=()):
        def var(name, value):
            return (f"\t\t\t\tflag={name}\n\t\t\t\tdata={{\n\t\t\t\t\ttype=value\n"
                    f"\t\t\t\t\tidentity={round(value * 1e5)}\n\t\t\t\t}}\n")
        block = "\tvariables={\n\t\tdata={ {\n" + "\t\t\t} {\n".join(
            var(n, v) for n, v in (("te_dg_sol", self.GAME_SOL), ("te_dg_lit", self.GAME_LIT), ("te_dg_m_inf", m_inf),
                                   ("te_dg_m_mat", m_mat), *extra) if v is not None
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

    STORED = (("te_dg_acc", 0.45), ("te_dg_trt_inf", 0.2), ("te_dg_trt_mat", 0.3), ("te_dg_trt_chr", 0.0),
              ("te_dg_in_ext", 0.0), ("te_dg_in_work", 0.0), ("te_dg_in_chr", 0.0), ("te_dg_in_turm", 0.5),
              ("te_dg_in_crowd", 0.0))

    def test_a_census_from_this_build_is_read_on_its_own_inputs(self):
        """The Causes of Death plan: medicine drifts, so the save's techs and laws give the targets, not what the step
        used. fidelity runs the model on the step's stored inputs."""
        stored = dict(self.STORED)
        inp = M.Inputs(sol=self.GAME_SOL, literacy=self.GAME_LIT, turmoil=0.5,
                       medicine={"access": 0.45, "infection": 0.2, "maternal": 0.3, "chronic": 0.0})
        mult = M.cause_multipliers(inp)
        path = self.save(False, mult["infection"], mult["maternal"] * H.P.MATERNAL_PER_100K_BIRTHS, extra=self.STORED)
        (_tag, _sid, _people, pairs, _sol, _lit), = H.fidelity_rows(path, DM.load_carriers())
        for cause in ("infection", "maternal"):
            game, model = pairs[cause]
            self.assertAlmostEqual(game / model, 1.0, places=4, msg=cause)
        self.assertEqual(stored["te_dg_in_turm"], H.census_inputs(inp, stored).turmoil)

    def test_a_census_from_before_reads_the_save(self):
        got = {"te_dg_sol": 8.0, "te_dg_lit": 0.2}
        inp = M.Inputs(sol=8.0, literacy=0.2)
        self.assertIs(H.census_inputs(inp, got), inp)

    def test_the_safety_shares_come_from_the_step_where_it_stored_them(self):
        """Modern safety (2026-10-16): a step's stored shares replace the owner's; a census whose step stored none keeps
        the owner's (the review of #979: history and practices-fit read no safety share and zeroed it)."""
        work, ext = H.P.SAFETY_TYPES["work"], H.P.SAFETY_TYPES["external"]
        inp = M.Inputs(sol=40.0, literacy=1.0, mods={work: 0.9, ext: 0.4})
        got = dict(self.STORED)
        kept = H.census_inputs(inp, got)
        self.assertEqual((kept.mods[work], kept.mods[ext]), (0.9, 0.4))
        got.update(te_dg_in_saf_work=0.5, te_dg_in_saf_ext=0.1)
        own = H.census_inputs(inp, got)
        self.assertEqual((own.mods[work], own.mods[ext]), (0.5, 0.1))
        self.assertTrue(set(H.SAFETY_VARS) <= set(H.FIDELITY_VARS))

    STEP_SOL, STEP_LIT = 12.0, 0.6   # the step's stored SoL and literacy, where a later walk moved the walk's

    def step_infection(self, sol, literacy):
        """The census's infection multiplier for the uncrowded state 1 at this SoL and literacy, on the save's
        techs and laws."""
        st = S.state_inputs(S.read_sections(self.save(False, 1.0)))["TST"][0][1]
        inp = H.inputs_for(st, DM.load_carriers())
        return M.cause_multipliers(M.Inputs(sol=sol, literacy=literacy, institutions=inp.institutions,
                                            mods=inp.mods))["infection"]

    def test_a_walk_without_a_step_is_not_a_mismatch(self):
        """#916: the step stores the SoL and literacy it used (te_dg_in_sol, te_dg_in_lit), and a walk without a step
        (a second pulse in a year, the console) rewrites te_dg_sol and te_dg_lit but never te_dg_m_*. fidelity runs
        the model on the stored pair, without needing all of CENSUS_INPUT_VARS (a census from before #916's last fix
        holds the other stored inputs but not these two, which came last)."""
        stored = (("te_dg_in_sol", self.STEP_SOL), ("te_dg_in_lit", self.STEP_LIT))
        m_inf = self.step_infection(self.STEP_SOL, self.STEP_LIT)
        self.assertNotAlmostEqual(m_inf / self.step_infection(self.GAME_SOL, self.GAME_LIT), 1.0, places=2,
                                  msg="the walk's figures must give another multiplier, or the test proves nothing")
        counts = {}
        (_tag, _sid, _people, pairs, sol, lit), = H.fidelity_rows(self.save(False, m_inf, extra=stored),
                                                                    DM.load_carriers(), counts=counts)
        game, model = pairs["infection"]
        self.assertAlmostEqual(game / model, 1.0, places=4)
        self.assertEqual(counts["stored"], 0, "read from the save: the stored SoL needs no other stored input")
        self.assertEqual((sol[1], lit[1]), (self.GAME_SOL, self.GAME_LIT), "the save's pops still beside the walk's")

    def test_the_stored_sol_and_literacy_with_the_steps_other_inputs(self):
        # a census from #916 on: the nine stored inputs and the stored SoL and literacy together
        inp = M.Inputs(sol=self.STEP_SOL, literacy=self.STEP_LIT, turmoil=0.5,
                       medicine={"access": 0.45, "infection": 0.2, "maternal": 0.3, "chronic": 0.0})
        mult = M.cause_multipliers(inp)
        extra = self.STORED + (("te_dg_in_sol", self.STEP_SOL), ("te_dg_in_lit", self.STEP_LIT))
        path = self.save(False, mult["infection"], mult["maternal"] * H.P.MATERNAL_PER_100K_BIRTHS, extra=extra)
        (_tag, _sid, _people, pairs, _sol, _lit), = H.fidelity_rows(path, DM.load_carriers())
        for cause in ("infection", "maternal"):
            game, model = pairs[cause]
            self.assertAlmostEqual(game / model, 1.0, places=4, msg=cause)

    def test_a_census_without_the_stored_sol_reads_the_walk(self):
        # a census from before #916: no te_dg_in_sol or te_dg_in_lit, so the walk's te_dg_sol and te_dg_lit
        m_inf = self.step_infection(self.GAME_SOL, self.GAME_LIT)
        (_tag, _sid, _people, pairs, _sol, _lit), = H.fidelity_rows(self.save(False, m_inf), DM.load_carriers())
        game, model = pairs["infection"]
        self.assertAlmostEqual(game / model, 1.0, places=4)

    def test_fidelity_counts_the_states_on_their_own_inputs(self):
        # the summary's lines: states read on the step's inputs, and those whose medicine is still spreading (the
        # tiny save's state has no health law, so access 0.45 is past its 0.4 target)
        mult = M.cause_multipliers(M.Inputs(sol=self.GAME_SOL, literacy=self.GAME_LIT))
        counts = {}
        H.fidelity_rows(self.save(False, mult["infection"], extra=self.STORED), DM.load_carriers(), counts=counts)
        self.assertEqual(counts, {"stored": 1, "save": 0, "spreading": 1})
        counts = {}
        H.fidelity_rows(self.save(False, mult["infection"] * 1.001), DM.load_carriers(), counts=counts)
        self.assertEqual(counts, {"stored": 0, "save": 1, "spreading": 0})

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


class TestLag(unittest.TestCase):
    """`lag`: years of life expectancy behind the target while medicine spreads (the Causes of Death plan, Task 3)."""

    @classmethod
    def setUpClass(cls):
        cls.rows = H.lag_rows()

    def test_every_scenario_starts_a_whole_gap_behind_and_closes(self):
        for label, rate, before, target, behind in self.rows:
            with self.subTest(label):
                self.assertAlmostEqual(behind[0], target - before, places=6)
                years = sorted(behind)
                self.assertTrue(all(behind[a] >= behind[b] - 1e-9 for a, b in zip(years, years[1:])), "never widens")
                self.assertGreaterEqual(behind[0], 0.0)

    def test_the_lag_closes_at_the_rate(self):
        # one step closes the rate's share of each input's gap; at a rate of 1 nothing is left after one step
        label, kw_before, kw_after = H.LAG_SCENARIOS[0]
        carriers = DM.load_carriers()
        after = H.scenario_inputs(carriers, **kw_after)
        fast = dataclasses.replace(after, mods={**after.mods, H.P.DIFFUSION_TYPE: 5.0})
        med = M.medicine_drift(M.medicine_targets(H.scenario_inputs(carriers, **kw_before)), fast)
        self.assertEqual(med, M.medicine_targets(fast))

    def test_the_cli_prints_every_scenario(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["lag"]), 0)
        for label, _b, _a in H.LAG_SCENARIOS:
            self.assertIn(label, out.getvalue())


class TestWorkforceCommand(unittest.TestCase):
    """Phase 2: the participation figures (the design §1.8's sketch) and step 2's bands (§5), on the fitted values."""

    @classmethod
    def setUpClass(cls):
        cls.rows = H.workforce_rows()
        cls.by = {r["name"]: r for r in cls.rows}

    def test_rows_cover_the_scenarios_and_the_1836_target(self):
        self.assertEqual([r["name"] for r in self.rows],
                         [s[0] for s in H.WORKFORCE_SCENARIOS] + ["Rich today (2020-like structure)"])
        farm = self.rows[0]
        self.assertAlmostEqual(farm["target"], 0.25, delta=0.02)
        for r in self.rows:
            # the rates are in the game's units (2026-10-20): the target is workers over people, with no scale
            self.assertAlmostEqual(r["target"], r["wa_share"] * r["at_work"], places=9)
            self.assertAlmostEqual(r["w_target"], r["target"] - P.WORKING_ADULT_BASE, places=12)

    def test_rich_today_meets_the_bands(self):
        """§5: 0.42 +- 0.03 on the engine's scale, women at least 0.8 of men's rate, about a fifth of over-65s at work,
        on a 2020-like structure (about 17% under 15 and 18% over 65)."""
        today = self.by["Rich today (2020-like structure)"]
        self.assertTrue(H.BAND_TODAY[0] <= today["engine"] <= H.BAND_TODAY[1], today["engine"])
        self.assertGreaterEqual(today["women"] / today["men"], H.BAND_WOMEN_TODAY)
        self.assertTrue(H.BAND_OLD_TODAY[0] <= today["all65"] <= H.BAND_OLD_TODAY[1], today["all65"])
        self.assertAlmostEqual(today["young"], 0.17, delta=0.03)
        self.assertAlmostEqual(today["old"], 0.18, delta=0.03)

    def test_most_old_men_work_with_no_pension(self):
        farm = self.by["1836 farming"]
        self.assertTrue(H.BAND_OLD_MEN_1836[0] <= farm["men65"] <= H.BAND_OLD_MEN_1836[1], farm["men65"])

    def test_outside_full_keeps_the_flat_lines(self):
        """The same state outside Full: the base and every moved line at its flat value (Women in the Fields +0.3)."""
        fields = self.by["1836 Women in the Fields"]
        self.assertAlmostEqual(fields["outside"], P.POP_BASE_RATIO_DEFAULT + 0.3, places=9)
        self.assertLess(fields["engine"], fields["outside"])

    def test_call_3s_laws_add_their_participation_inputs(self):
        """A Pro-Capital Ministry at level 5 and Rehabilitation add about +0.027 on the engine's scale to the rich row
        (the design §1.7's inventory, on its stable structure), against +0.15 as flat lines."""
        rows = {r["name"]: r for r in self.rows}
        gain = rows["Rich, plus call 3's laws"]["target"] - rows["Rich, Protected Class, pension at 65"]["target"]
        self.assertGreater(gain, 0.015)
        self.assertLess(gain, 0.04)

    def test_the_command_prints_a_row_per_scenario(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["workforce"]), 0)
        for name, _kw, _low in H.WORKFORCE_SCENARIOS:
            self.assertIn(name, out.getvalue())


class TestPensionsCommand(unittest.TestCase):
    """Phase 2 step 2: the pension bill fitted against the game's revenue, the health bill (the design §5)."""

    def test_revenue_share_is_the_largest_economies_median(self):
        budgets = {"A": {"gdp": 1000.0, "income": 1000 * 0.2 / 52}, "B": {"gdp": 500.0, "income": 500 * 0.3 / 52},
                   "C": {"gdp": 10.0, "income": 10 * 0.9 / 52}}
        median, ratios = H.revenue_share(budgets, top=2)
        self.assertAlmostEqual(median, 0.25)
        self.assertEqual([t for t, _ in ratios], ["A", "B"])

    def test_b_centres_the_band(self):
        b = H.fitted_b(0.27)
        self.assertAlmostEqual(0.2 * b * H.PENSION_LEVEL / 0.27, sum(P.PENSION_BILL_BAND) / 2)

    def test_the_fitted_b_meets_the_band_at_the_1953_ratio(self):
        """The fit (2026-10-12): the 1953 save's 15 largest economies' median revenue over GDP was 0.273; at it the
        bill for 18-22% pensioners at Social Security 5 sits inside 15-30% of revenue."""
        for share in H.PENSION_SHARES:
            bill = M.pension_bill_gdp_share(share, H.PENSION_LEVEL) / 0.273
            self.assertTrue(P.PENSION_BILL_BAND[0] <= bill <= P.PENSION_BILL_BAND[1], (share, bill))

    def test_the_health_bill_meets_its_bands(self):
        for label, _need, term, (lo, hi) in H.health_rows():
            self.assertTrue(lo <= term <= hi, (label, term))

    def test_the_command_runs_without_a_save(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["pensions"]), 0)
        self.assertIn("The health bill", out.getvalue())

class TestConsequences(unittest.TestCase):
    """`consequences`: phase 2 step 4's bands (docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-
    design.md §5) on the model's structures and on a census save."""

    def test_the_stable_structures(self):
        rows = {r["name"]: r for r in H.consequence_scenarios()}
        self.assertLess(abs(rows["1836 agrarian (reference)"]["term"]), 0.02)
        rich = next(r for name, r in rows.items() if name.startswith("Rich"))
        self.assertTrue(H.BAND_RICH_TERM[0] <= rich["term"] <= H.BAND_RICH_TERM[1], rich["term"])
        for r in rows.values():
            self.assertLess(r["youth"], P.YOUTH_FROM, r["name"])

    @unittest.mock.patch.object(P, "SEX_BALANCE_EFFECTS", True)   # judged as if on (held back: the switch)
    def test_the_sex_anchors(self):
        for name, _b, got, bands in H.sex_anchor_rows():
            for key, (lo, hi) in bands.items():
                self.assertTrue(lo - 1e-9 <= got[key] <= hi + 1e-9, (name, key, got[key]))

    def test_a_sharp_transition_reaches_the_youth_bulge(self):
        slow, fast = H.consequence_transitions(years=50)
        self.assertGreater(fast["peak_youth"], 0.21)
        self.assertGreater(fast["y"], 0.5)
        self.assertLessEqual(fast["y"], 1.0)
        self.assertLess(slow["y"], fast["y"])
        # no ceiling on the term (owner, 2026-10-16): the pool of a sharp transition lifts it past the old +0.25 (0.41)
        self.assertGreater(fast["peak_term"], 0.25)
        self.assertLess(fast["peak_term"], 0.6)

    def _census_save(self, tmp):
        from test_demographics_save_inputs import TINY
        bands = {f"te_dg_b{s}{b}": 1000.0 for s in "fm" for b in range(P.BANDS)}
        bands.update(te_dg_bm4=2000.0, te_dg_bm5=1800.0, te_dg_bf4=1500.0, te_dg_bf5=1500.0, te_dg_bm7=500.0)
        people = sum(bands.values())
        variables = {**bands, "te_dg_people": people, "te_dg_sex_balance": 132.0}

        def var(name, value):
            return (f"\t\t\t\tflag={name}\n\t\t\t\tdata={{\n\t\t\t\t\ttype=value\n"
                    f"\t\t\t\t\tidentity={round(value * 1e5)}\n\t\t\t\t}}\n")
        block = "\tvariables={\n\t\tdata={ {\n" + "\t\t\t} {\n".join(var(n, v) for n, v in variables.items()) + \
            "\t\t\t} }\n\t}\n"
        state = "1={\n\tcountry=3\n\tincorporation=1\n"
        path = Path(tmp) / "census.v3"
        path.write_text(TINY.replace(state + "}", state + block + "}", 1), encoding="utf-8")
        return str(path), bands, people

    @unittest.mock.patch.object(P, "SEX_BALANCE_EFFECTS", True)   # judged as if on (held back: the switch)
    def test_a_census_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, bands, people = self._census_save(tmp)
            figs = H.census_figures(path)
            self.assertEqual(set(figs), {"1"})
            f = figs["1"]
            self.assertAlmostEqual(f["people"], people, places=3)
            self.assertAlmostEqual(f["fam"], sum(bands[f"te_dg_bm{b}"] for b in (4, 5, 6, 7)), places=3)
            youth = sum(bands[f"te_dg_b{s}{b}"] for s in "fm" for b in (4, 5)) / people
            self.assertAlmostEqual(f["youth"], youth, places=6)
            r = H.save_consequences(path)
            self.assertAlmostEqual(r["term_world"], M.conscription_term(f["fam"], people), places=9)
            # TINY's only pop with a workforce has no workplace: unemployment 1
            self.assertAlmostEqual(r["y_any"], 1.0 if M.youth_bulge(youth, 1.0) > 0 else 0.0)
            self.assertEqual((r["fewer"], r["more"], r["either"]), (0.0, 1.0, 1.0))
            out = io.StringIO()
            with redirect_stdout(out):
                H.main(["consequences", path])
            self.assertIn("1 census states", out.getvalue())
            self.assertIn("the first save's world term", out.getvalue())

    def test_the_sex_band_is_judged_while_on_and_on_request_while_held_back(self):
        """On (the migrant booking, 2026-10-12) the sex band and anchors are judged; held back, only with --effects (or its
        older name --sex-effects), which restores the switches."""
        self.assertTrue(P.SEX_BALANCE_EFFECTS and P.CONSCRIPTION_EFFECTS and P.YOUTH_BULGE_EFFECTS)
        with tempfile.TemporaryDirectory() as tmp:
            path, _bands, _people = self._census_save(tmp)
            out = io.StringIO()
            with redirect_stdout(out):
                H.main(["consequences", path])
            self.assertIn("sex balance: ", out.getvalue())
            self.assertNotIn("Held back in game", out.getvalue())
            off = [unittest.mock.patch.object(P, attr, False) for attr in H.HELD_BACK]
            for patch in off:
                patch.start()
            try:
                for flag, shown in (([], False), (["--effects"], True), (["--sex-effects"], True)):
                    out = io.StringIO()
                    with redirect_stdout(out):
                        H.main(["consequences", path, *flag])
                    self.assertEqual("sex balance: " in out.getvalue(), shown, flag)
                    self.assertEqual("Soviet Union 1959" in out.getvalue(), shown, flag)
                    self.assertIn("Held back in game: CONSCRIPTION_EFFECTS, YOUTH_BULGE_EFFECTS, SEX_BALANCE_EFFECTS",
                                  out.getvalue())
                    self.assertFalse(P.SEX_BALANCE_EFFECTS or P.CONSCRIPTION_EFFECTS or P.YOUTH_BULGE_EFFECTS)
            finally:
                for patch in off:
                    patch.stop()


class TestRebook(unittest.TestCase):
    """`rebook`: the census re-walked through a run's saves with its own residual (the migrant booking, 2026-10-12;
    demographics_rebook.py), on a synthetic run in extract_all.py's per-save JSON."""

    INP = M.Inputs(sol=8, literacy=0.1, urban_share=0.05, female_job_share=0.02)

    def _run(self, tmp, years=40, rate=-0.04):
        import demographics_rebook as RB
        ring = M.seed(self.INP, 1837, 1_000_000.0)
        people = ring.people()
        paths = []
        for i in range(years + 1):
            year = 1837 + i
            v = {"te_dg_year": float(year), "te_dg_stepped": 0.0 if i == 0 else 1.0, "te_dg_people": people,
                 "te_dg_net_migration": 0.0 if i == 0 else rate * people, "te_dg_sol": 8.0, "te_dg_lit": 0.1,
                 "te_dg_urban_share": 0.05, "te_dg_fjob_share": 0.02, "te_dg_inflow_years": 0.0,
                 "te_dg_scale": ring.scale, "te_dg_pf": 0.0, "te_dg_pm": 0.0, "te_dg_pa": 150.0}
            v.update({f"te_dg_b{s}{b}": 1000.0 for s in "fm" for b in range(P.BANDS)})
            state = {"country": "3", "region": "STATE_TEST", "devastation": 0.0, "vars": v}
            if i == 0:
                state["ring"] = {"f": {str(k): x for k, x in enumerate(ring.f) if x},
                                 "m": {str(k): x for k, x in enumerate(ring.m) if x}}
            data = {"date": f"{year + 1}.1.1", "states": {"7": state}, "countries": {"3": {"tag": "AAA"}},
                    "laws": {"3": ["law_no_womens_rights"]}, "techs": {}, "wars": []}
            path = Path(tmp) / f"s{i:03d}.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            paths.append(str(path))
            people *= 0.985
        return RB, [RB.read_save(p) for p in paths]

    def test_sustained_emigration_hollows_the_profile_alone_not_the_booking(self):
        with tempfile.TemporaryDirectory() as tmp:
            RB, saves = self._run(tmp)
            saves = RB.merge_years(saves)
            booked, before = RB.walk(saves), RB.walk(saves, booked=False)
            last = saves[-1]["year"]
            self.assertLess(before["7"][last]["sb"], P.SEX_FEWER_FROM, "the bug: the young men leave year after year")
            self.assertGreater(booked["7"][last]["sb"], P.SEX_FEWER_FROM)
            self.assertGreater(booked["7"][last]["T"], before["7"][last]["T"])
            self.assertEqual(P.MIGRANT_CAP_OUT, 0.03, "the walk restores the booking after the profile-alone pass")
            r = RB.band_summary([booked["7"][last]])
            self.assertEqual((r["n"], r["fewer"], r["either"]), (1, 0.0, 0.0))
            terms = RB.country_terms(booked, saves, ["AAA"], [last])
            self.assertAlmostEqual(terms["AAA"][last], booked["7"][last]["T"], places=9)
            # the save's own bands are flat (1000 a band): 100 men per 100 women
            med, *_rest, out_save, _out_walk = RB.fidelity(booked, saves, last)
            self.assertAlmostEqual(med, booked["7"][last]["sb"] - 100.0, places=6)
            self.assertEqual(out_save, 0.0)

    def test_the_profiles_carriers_reach_the_inputs(self):
        # the rebook reads the women's work share and the families' line from the game files (modifier-types stage 3)
        import demographics_rebook as RB
        techs = frozenset({"paddle_steamer", "railways", "combustion_engine", "commercial_aviation",
                           "jet_engine_technology"})
        self.assertEqual(RB.transport_techs(), techs)
        self.assertEqual(RB.women_laws(), frozenset({"law_women_in_the_fields", "law_women_own_property",
                                                     "law_women_in_the_workplace", "law_womens_suffrage",
                                                     "law_protected_class"}))
        country = {"laws": frozenset({"law_protected_class"}), "techs": techs, "at_war": False}
        inp = RB.inputs({"owner": "3", "vars": {}}, None, country, 1990, {})
        self.assertAlmostEqual(M.female_work_share(inp), 0.48, places=9)
        self.assertAlmostEqual(inp.mods[P.FAMILY_MIGRATION_TYPE], 0.45, places=9)

    def test_a_seed_in_the_save_seeds_the_walk(self):
        with tempfile.TemporaryDirectory() as tmp:
            RB, saves = self._run(tmp, years=12)
            saves[6]["states"]["7"]["vars"]["te_dg_stepped"] = 0.0   # the game seeded this state again that year
            walked = RB.walk(saves, booked=False)
            year = saves[6]["year"]
            self.assertAlmostEqual(walked["7"][year]["sb"], M.consequence_figures(
                M.seed(RB.inputs(saves[6]["states"]["7"], None, saves[6]["countries"]["3"], year, {}), 1843,
                       saves[6]["states"]["7"]["vars"]["te_dg_people"]))["sex_balance"], places=6)
            self.assertLess(walked["7"][saves[5]["year"]]["sb"], walked["7"][year]["sb"])

    def test_the_command_judges_the_bands(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._run(tmp, years=12)
            out = io.StringIO()
            with redirect_stdout(out):
                code = H.main(["rebook", *sorted(str(p) for p in Path(tmp).glob("*.json")), "--years", "1850"])
            self.assertEqual(code, 0)
            text = out.getvalue()
            self.assertIn("note: no plain-text save", text)
            self.assertIn("booked        1 states", text)
            self.assertIn("band under 2%: ok", text)
            self.assertIn("Great powers' conscription terms by decade (booked)", text)


if __name__ == "__main__":
    unittest.main()
