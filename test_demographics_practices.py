"""scripts/analysis/demographics_practices.py: Late Marriage and Birth Spacing in the harness
(docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md, Tasks 3-5)."""

import json
import sys
import tempfile
import unittest
from unittest import mock
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_practices as DP  # noqa: E402
import demographics_save_inputs as S  # noqa: E402


def _state(sid, state_region, strategic_region, people=1000.0, tag="TST", incorporated=True, **inp):
    return DP.PracticeState(sid, tag, state_region, strategic_region, people, incorporated, M.Inputs(**inp))


class TestInputs(unittest.TestCase):
    def test_a_saves_own_shares_are_read(self):
        """Stop B, M2: a save from a build with the practices holds each census state's te_dg_pr_*; the harness reads
        them (practice_states' `stored`, saved_shares), and the fit and history start from them, not the table."""
        c = S.CountryInputs("TST")
        c.population, c.sol_x_size, c.wealth_tfr_x_size = 1000.0, 8000.0, M.wealth_tfr(8.0) * 1000.0
        c.workforce, c.literate = 500.0, 100.0
        sections = {"states": {"1": {"region": '"STATE_POSEN"'}, "2": {"region": '"STATE_POSEN"'}}}
        svars = {"1": {"vars": {"te_dg_pr_lm": 0.55, "te_dg_pr_bs": 0.0}}, "2": {"vars": {"te_dg_pr_lm": 0.5}}}
        with mock.patch.object(DP.S, "state_inputs", return_value={"TST": [("1", c, True), ("2", c, True)]}):
            states = DP.practice_states("x.v3", [], regions={"STATE_POSEN": "region_eastern_europe"},
                                        save=(sections, svars))
        self.assertEqual({s.sid: s.stored for s in states}, {"1": {"lm": 0.55, "bs": 0.0}, "2": {}},
                         "a state holding only some of the shares holds none")
        self.assertEqual(DP.saved_shares(states), {"1": {"lm": 0.55, "bs": 0.0}})
        self.assertIn("te_dg_pr_lm", DP.H.PRACTICE_VARS)

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


    def test_a_parsed_save_walks_its_pops_once(self):
        """practices-fit re-runs the model at every grid point from the cached parse (Task 5): the pops' walk
        (S.state_inputs), which no grid point changes, runs once a parsed save."""
        save = ({"states": {}}, {})
        with mock.patch.object(DP.S, "state_inputs", return_value={}) as walk:
            DP.practice_states("x.v3", [], regions={}, save=save)
            DP.practice_states("x.v3", [], regions={}, save=save)
            self.assertEqual(walk.call_count, 1)
            DP.practice_states("x.v3", [], regions={}, save=({"states": {}}, {}))
            self.assertEqual(walk.call_count, 2, "another parse is walked again")

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

    def test_a_whole_region_changing_hands_takes_the_regions_copy(self):
        """Stop B, I1 (owner, 2026-10-12): each step writes the shares to the state region (te_dg_pr_<P>_r). A whole
        region changing hands reappears under a new ID with no sibling; its seed takes the region's copy, not the eroded
        start, in the game and in the replay alike."""
        old = _state("1", "STATE_POSEN", "region_eastern_europe", people=3000.0, mods={P.CONTRACEPTION_TYPE: 1.0},
                     literacy=1.0)
        new = _state("2", "STATE_POSEN", "region_eastern_europe", people=3100.0)
        got = DP.replay([(1877, [old]), (1887, [new])])
        carried = got[1877]["1"]["lm"]
        for _ in range(9):                                     # 1878-1886 at 1877's conditions
            carried = M.practice_drift(carried, M.practice_target("lm", old.inp, 0.8))
        want = M.practice_drift(carried, M.practice_target("lm", new.inp, 0.8))   # then 1887's step
        self.assertAlmostEqual(got[1887]["2"]["lm"], want, places=9)
        self.assertLess(got[1887]["2"]["lm"], 0.5, "not re-seeded at the table's 0.8")

    def test_the_regions_copy_is_the_last_stepped_states(self):
        """In a split region each step overwrites the copy, so it holds the last state to step (in the replay, the
        save's last state of the region), not a mean: a fallback, not a census of the region."""
        a = _state("1", "STATE_POSEN", "region_eastern_europe", people=3000.0, mods={P.CONTRACEPTION_TYPE: 1.0},
                   literacy=1.0)
        b = _state("3", "STATE_POSEN", "region_eastern_europe", people=1000.0)
        new = _state("2", "STATE_POSEN", "region_eastern_europe", people=4000.0)
        got = DP.replay([(1876, [a, b]), (1877, [a, b]), (1878, [new])])
        self.assertAlmostEqual(got[1878]["2"]["lm"], M.practice_drift(got[1877]["3"]["lm"],
                                                                      M.practice_target("lm", new.inp, 0.8)), places=9)

    def test_a_sibling_wins_over_the_regions_copy(self):
        """The region's copy is a fallback: a split state with a sibling holding shares takes the sibling's."""
        first = _state("1", "STATE_POSEN", "region_eastern_europe", people=3000.0, mods={P.CONTRACEPTION_TYPE: 1.0},
                       literacy=1.0)
        other = _state("3", "STATE_POSEN", "region_eastern_europe", people=1000.0)
        # 1877: both hold shares; the copy is whichever stepped last. 1878: "1" is gone, "2" is new beside "3"
        new = _state("2", "STATE_POSEN", "region_eastern_europe", people=3000.0)
        got = DP.replay([(1876, [first, other]), (1877, [first, other]), (1878, [other, new])])
        # "2" seeds at its sibling's 1877 share, then takes 1878's step at its own conditions
        self.assertAlmostEqual(got[1878]["2"]["lm"], M.practice_drift(got[1877]["3"]["lm"],
                                                                      M.practice_target("lm", new.inp, 0.8)), places=9)
        self.assertNotAlmostEqual(got[1877]["3"]["lm"], got[1877]["1"]["lm"], places=3, msg="the copy would differ")

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


def _fit(country, base, lm=0.0, bs=0.0, held=None, people=1e7, e0=35.0, tag="TST", sid="1", deaths=300.0):
    return DP.FitState(sid, country, tag, people, True, base, 0.4, e0, deaths, lm, bs, held)


class TestFit(unittest.TestCase):
    ANCHORS = {"tfr": {"Sweden": {1837: 4.4}, "Iran": {1837: 7.0}, "China": {1837: 5.5}}}

    def test_a_point_scales_the_curve_and_applies_the_cuts(self):
        states = {1837: [_fit("Sweden", 5.5, lm=1.0), _fit("Iran", 6.0)]}
        got = DP.evaluate(states, self.ANCHORS, s=1.15, cut_lm=0.3, cut_bs=0.35)
        self.assertAlmostEqual(got["countries"][("Sweden", 1837)][0], 5.5 * 1.15 * 0.7, places=9)
        self.assertAlmostEqual(got["countries"][("Iran", 1837)][0], 6.0 * 1.15, places=9)
        want = ((5.5 * 1.15 * 0.7 - 4.4) ** 2 + 0.5 * (6.0 * 1.15 - 7.0) ** 2) / 1.5
        self.assertAlmostEqual(got["error"], want ** 0.5, places=9)

    def test_the_held_share_cancels_the_raise(self):
        china = _fit("China", 6.0, bs=P.BS_EAST_ASIA_START, held="east_asia")
        india = _fit("India", 6.0, bs=P.BS_HELD_START, held="india", sid="2", tag="BIC")
        got = DP.evaluate({1837: [china, india]}, self.ANCHORS, s=1.2, cut_lm=0.3, cut_bs=0.4)
        self.assertAlmostEqual(got["held"], (1 - 1 / 1.2) / 0.4, places=9)
        self.assertAlmostEqual(got["east"], got["held"], places=9, msg="East Asia defaults to the cancel share")
        self.assertAlmostEqual(got["countries"][("China", 1837)][0], 6.0, places=9)
        # owner, 2026-10-11 (D13): East Asia's share may sit above it; India's stays
        above = DP.evaluate({1837: [china, india]}, self.ANCHORS, s=1.2, cut_lm=0.3, cut_bs=0.4, east=0.6)
        self.assertAlmostEqual(above["countries"][("China", 1837)][0], 6.0 * 1.2 * (1 - 0.4 * 0.6), places=9)
        self.assertAlmostEqual(above["countries"][("India", 1837)][0], 6.0, places=9)

    def test_a_held_group_with_a_zero_start_takes_the_held_share(self):
        """A fit that lands a held start at 0 (no raise to cancel; Task 6) leaves nothing for a replay to erode: the
        state takes the held share itself, not a division by zero."""
        china = _fit("China", 6.0, bs=0.0, held="east_asia")
        india = _fit("India", 6.0, bs=0.0, held="india", sid="2", tag="BIC")
        with DP.patch_params(BS_EAST_ASIA_START=0.0, BS_HELD_START=0.0):
            self.assertAlmostEqual(DP.tfr_at(china, 1.2, 0.3, 0.4, 0.1, 0.5), 6.0 * 1.2 * (1 - 0.4 * 0.5), places=9)
            self.assertAlmostEqual(DP.tfr_at(india, 1.2, 0.3, 0.4, 0.1, 0.5), 6.0 * 1.2 * (1 - 0.4 * 0.1), places=9)
            self.assertAlmostEqual(DP.tfr_at(china, 1.0, 0.3, 0.4, 0.0, 0.0), 6.0, places=9)

    def test_the_table_finds_each_raises_best_cuts(self):
        states = {1837: [_fit("Sweden", 5.5, lm=1.0), _fit("Iran", 6.0)]}
        rows = DP.fit_table(states, self.ANCHORS, [1.15], [0.2, 0.3, 0.4], [0.35])
        self.assertEqual(len(rows), 1)
        s, cut_lm, _cut_bs, _res = rows[0]
        # Sweden's 4.4 at 5.5 x 1.15 wants 1 - cut = 0.696: 0.3 is the grid's nearest
        self.assertEqual((s, cut_lm), (1.15, 0.3))

    def test_patch_params_restores(self):
        before = (P.POVERTY_INFECTION_AT_FLOOR, P.INFECTION["f"][0], dict(P.PRACTICE_CUT))
        with DP.patch_params(infection_scale=1.2, POVERTY_INFECTION_AT_FLOOR=2.0, PRACTICE_CUT={"lm": 0.2, "bs": 0.3}):
            self.assertEqual(P.POVERTY_INFECTION_AT_FLOOR, 2.0)
            self.assertAlmostEqual(P.INFECTION["f"][0], before[1] * 1.2)
            self.assertEqual(P.PRACTICE_CUT, {"lm": 0.2, "bs": 0.3})
        self.assertEqual((P.POVERTY_INFECTION_AT_FLOOR, P.INFECTION["f"][0], P.PRACTICE_CUT), before)

    def test_band_deaths(self):
        q = [1000.0] * len(P.GROUPS)
        bands = [(100.0, 50.0)] * P.BANDS
        self.assertAlmostEqual(DP.band_deaths(q, q, bands), P.BANDS * 150.0 * 1000 / 100000)


class TestProjection(unittest.TestCase):
    """Review C1: #904's peacetime births less deaths, projected to a point of the fit, and the regional gate."""

    ROWS = [
        # step year, group, peace, reasons, births, deaths, people, migration, tag, state id
        [1836, "China", True, [], 42.5, 36.0, 1000.0, 0.0, "CHI", "1"],
        [1836, "Middle East, C Asia", True, [], 41.5, 32.7, 1000.0, 0.0, "PER", "2"],
        [1836, "Middle East, C Asia", False, ["war"], 90.0, 10.0, 1000.0, 0.0, "PER", "2"],   # not peacetime
        [1836, "W/N/C/S Europe", True, [], 37.9, 26.8, 1000.0, 0.0, "GBR", "3"],
    ]

    def states(self, deaths=300.0):
        return {1837: [_fit("China", 6.0, bs=P.BS_EAST_ASIA_START, held="east_asia", sid="1", tag="CHI",
                            deaths=deaths),
                       _fit("Iran", 6.0, sid="2", tag="PER", deaths=deaths),
                       _fit("United Kingdom", 5.5, lm=1.0, sid="3", tag="GBR", deaths=deaths)]}

    def test_today_is_the_measured_rate(self):
        today = self.states()
        proj = DP.project_regions(self.ROWS, today, today, s=1.0, cut_lm=0.0, cut_bs=0.35)
        self.assertAlmostEqual(proj["groups"]["China"][1], 6.5, places=9)
        self.assertAlmostEqual(proj["groups"]["Middle East, C Asia"][0], 8.8, places=9, msg="war rows left out")
        self.assertAlmostEqual(proj["world"][0], (6.5 + 8.8 + 11.1) / 3, places=9)

    def test_births_take_the_points_children_per_woman_and_deaths_its_mortality(self):
        today = self.states()
        point = self.states(deaths=330.0)                     # the mortality knobs raised deaths 10% everywhere
        proj = DP.project_regions(self.ROWS, today, point, s=1.15, cut_lm=0.3, cut_bs=0.35)
        self.assertAlmostEqual(proj["groups"]["China"][1], 42.5 * 1.0 - 36.0 * 1.1, places=6, msg="held")
        self.assertAlmostEqual(proj["groups"]["Middle East, C Asia"][1], 41.5 * 1.15 - 32.7 * 1.1, places=6)
        self.assertAlmostEqual(proj["groups"]["W/N/C/S Europe"][1], 37.9 * 1.15 * 0.7 - 26.8 * 1.1, places=6)

    def test_east_asias_share_brings_china_into_its_band(self):
        """Owner, 2026-10-11 (D13): the smallest share on a 0.01 grid, at least the cancel share, at which China's projected
        peacetime births less deaths is at most +6. Here +6.5 at the cancel share; 42.5 x 1.15 x (1 - 0.35 e) - 36 <= 6
        needs e >= 0.402, so 0.41."""
        today = self.states()
        e, rate = DP.east_for_china(self.ROWS, today, today, s=1.15, cut_lm=0.3, cut_bs=0.35)
        self.assertAlmostEqual(e, 0.41, places=9)
        self.assertLessEqual(rate, 6.0)
        # already in band at the cancel share: the cancel share (rounded up to the grid)
        low = [[1836, "China", True, [], 40.0, 36.0, 1000.0, 0.0, "CHI", "1"]]
        e, rate = DP.east_for_china(low, today, today, s=1.15, cut_lm=0.3, cut_bs=0.35)
        self.assertAlmostEqual(e, 0.38, places=9)

    def test_the_gate_prints_two_decimals(self):
        """Stop B, M4: at one decimal a miss by 0.01 printed as the band's own edge (+8.0 against +8 to +10)."""
        proj = {"groups": {"W/N/C/S Europe": (11.07, 7.99)}, "world": (8.75, 7.83), "tags": {"JAP": (5.4e7, 8.4, -0.04)}}
        fails = DP.region_gate(proj)
        self.assertIn("W/N/C/S Europe: +7.99 per 1,000 (history +8 to +10)", fails)
        self.assertIn("World: +7.83 per 1,000 (at most +7.75)", fails)
        self.assertIn("JAP: -0.04 per 1,000 with 54M people", fails)

    def test_the_span_is_904s_table(self):
        """#904's table covers the steps of 1837-1900 (its analyze.py's intervals, 1837 to 1901); its rows also hold
        1901's, from the 1902 save, which the table leaves out. The projection reads the table's span, so its measured
        column reproduces #904's."""
        rows = [[year, "China", True, [], 40.0, 30.0, 1000.0, 0.0, "CHI", "1"] for year in (1836, 1837, 1900, 1901)]
        self.assertEqual([r[0] for r in DP.peacetime_span(rows)], [1837, 1900])

    def test_the_gate(self):
        today = self.states()
        proj = DP.project_regions(self.ROWS, today, today, s=1.15, cut_lm=0.3, cut_bs=0.35)
        fails = DP.region_gate(proj)
        self.assertTrue(any(line.startswith("China:") for line in fails), "+6.5 is above China's +3 to +6")
        self.assertTrue(any(line.startswith("Middle East, C Asia:") for line in fails))
        self.assertTrue(any(line.startswith("World:") for line in fails))
        quiet = {"groups": {"China": (6.5, 5.0)}, "world": (8.8, 7.0), "tags": {"CHI": (4e8, 6.5, 5.0)}}
        self.assertEqual(DP.region_gate(quiet), [])
        shrinking = dict(quiet, tags={"CHI": (4e8, 6.5, -0.1)})
        self.assertEqual(len(DP.region_gate(shrinking)), 1)


if __name__ == "__main__":
    unittest.main()
