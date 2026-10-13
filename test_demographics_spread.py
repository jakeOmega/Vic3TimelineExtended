"""Phase 3's spreading machinery: Family Limitation as a national practice, Cultural Hegemony's drift on desired
fertility, and the practices' neighbour spread (docs/superpowers/specs/2026-10-08-demographics-design.md section 13
and section 6; the late-marriage spec 4.4).

The script (te_demog_fl_effects.txt, te_demog_practice_effects.txt and the generated te_demog_spread_*) runs through
test_demographics_registry's interpreter against demographics_model's twins; the harness's replay
(demographics_fl.py, demographics_practices.neighbour_map) and the adjacency snapshot are checked on small cases.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_adjacency as A  # noqa: E402
import demographics_fl as F  # noqa: E402
import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
import demographics_practices as DP  # noqa: E402
from test_demographics_registry import (  # noqa: E402  (helpers and paths only)
    EFFECTS, FL_EFFECTS, PRACTICE_EFFECTS, SPREAD_EFFECTS, SPREAD_VALUES, VALUES, _block, _engine_for,
    _OwnerEngine, _text)

FAST_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_fast_effects.txt"
DEBUG_EFFECTS = ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt"
DEBUG_EVENTS = ROOT / "events" / "te_debug_demog_events.txt"
HISTORY = ROOT / "common" / "history" / "extra_history.txt"
DEMOG_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_modifiers.txt"
PLAYTEST = ROOT / "docs" / "testing" / "demographics-playtest.md"


class _CountryEngine(_OwnerEngine):
    """A country under Full: its laws (has_law, has_law_or_variant), its neighbouring states (each a dict of the state's
    variables with its state_population, `_root` True where the country owns it, `_owner` its owner's variables) and
    the hegemon's variables (global_var:ch_rank_1 = { }; None: no hegemon)."""

    def __init__(self, fixtures, laws=(), hegemon=None, **kwargs):
        super().__init__(fixtures, laws=laws, triggers={"te_demog_effects_run": True, "te_demog_cohorts_run": True},
                         **kwargs)
        self.hegemon = hegemon

    def _test(self, key, op, arg):
        if key == "has_law_or_variant":
            variants = {"law_state_religion": {"law_millet_system", "law_people_of_the_book"}}.get(arg[9:], set())
            return arg[9:] in self.laws or bool(variants & self.laws)
        if key == "exists" and arg == "global_var:ch_rank_1":
            return self.hegemon is not None
        if key == "exists" and arg == "owner":
            return "_owner" in self.vars
        if key == "owner" and arg == "ROOT":
            return bool(self.vars.get("_root"))
        if key == "owner" and isinstance(arg, list):
            saved, self.vars = self.vars, self.vars["_owner"]
            try:
                return self.holds(arg)
            finally:
                self.vars = saved
        return super()._test(key, op, arg)

    def number(self, tok):
        if tok.startswith("owner.var:"):
            return self.vars["_owner"][tok[10:]]
        return super().number(tok)

    def run(self, items):
        rest = []
        for item in items:
            if item[0] == "global_var:ch_rank_1":
                self.run(rest)
                rest = []
                saved, self.vars = self.vars, self.hegemon
                try:
                    self.run(item[2])
                finally:
                    self.vars = saved
            else:
                rest.append(item)
        super().run(rest)


def _country(agr=0.7, lit=0.3, ero=0.0, laws=(), share=None, history_modifier=False, neighbours=(), exposure=0.0,
             hegemon=None, desired=None, ch=None, undivided=False):
    eng = _CountryEngine({"te_demog_ch_exposure": exposure}, laws=laws, hegemon=hegemon)
    eng.trigger_fixtures["te_inh_has_undivided_farms"] = undivided
    eng.vars.update(te_dg_fl_agr=agr, te_dg_fl_lit=lit, te_dg_fl_ero=ero)
    if share is not None:
        eng.vars["te_dg_pr_fl"] = share
    if desired is not None:
        eng.vars["te_dg_desired"] = desired
    if ch is not None:
        eng.vars["te_dg_ch_desired"] = ch
    if history_modifier:
        eng.modifiers["te_demog_family_limitation"] = 1.0
    eng.neighbours = [dict(n) for n in neighbours]
    return eng


def _neighbour(people, share=None, root=False):
    owner = {} if share is None else {"te_dg_pr_fl": share}
    return {"state_population": people, "_root": root, "_owner": owner}


class TestFamilyLimitationModel(unittest.TestCase):
    def test_the_target(self):
        heir = {"law_equal_inheritance", "law_freedom_of_conscience"}
        self.assertAlmostEqual(M.fl_target(0.74, 0.3, heir), P.FL_HEIRSHIP * 0.74)
        self.assertEqual(M.fl_target(0.74, 0.3, heir, undivided=True), 0.0, "Undivided Farm Succession: no cut to fold")
        self.assertEqual(M.fl_target(0.74, 0.3, {"law_partible"}), 0.0, "1836's other countries start with no target")
        full = M.fl_target(0.0, 1.0, {"law_total_separation"})
        self.assertAlmostEqual(full, P.FL_LITERACY * P.FL_CHURCH["law_total_separation"])
        self.assertAlmostEqual(M.fl_target(0.0, 1.0, {"law_millet_system"}),
                               P.FL_LITERACY * P.FL_CHURCH["law_state_religion"], msg="a variant takes its parent's")
        self.assertEqual(M.fl_target(1.0, 1.0, heir | {"law_total_separation"}), 1.0, "at most 1")

    def test_the_step_rises_only(self):
        self.assertEqual(M.fl_step(0.6, 0.0, 0.0), 0.6, "France keeps its share when its conditions fall")
        self.assertAlmostEqual(M.fl_step(0.0, 0.0, 0.3), P.FL_SPREAD * 0.3)
        self.assertAlmostEqual(M.fl_step(0.1, 0.5, 0.3), 0.1 + P.FL_RATE * 0.4 + P.FL_SPREAD * 0.2)
        self.assertEqual(M.fl_step(0.2, 0.1, None), 0.2)

    def test_the_line(self):
        self.assertEqual(M.fl_line(0.6), 0.6)
        self.assertAlmostEqual(M.fl_line(0.6, 0.7), 0.6 * 0.3 if P.FL_ERODES else 0.6)
        self.assertEqual(M.fl_line(P.FL_LINE_MIN / 2), 0.0, "no line below the floor")
        self.assertEqual(M.fl_seed(True), P.FAMILY_LIMITATION_MEANS)
        self.assertEqual(M.fl_seed(False), 0.0)

    def test_frances_start_is_todays_line(self):
        """Nothing changes in France's means at the swap: history's +0.6 becomes the practice's line at 0.6."""
        self.assertEqual(M.fl_line(M.fl_seed(True)), P.FAMILY_LIMITATION_MEANS)
        body = re.sub(r"#[^\n]*", "", _block(_text(DEMOG_MODIFIERS), "te_demog_family_limitation"))
        self.assertIn(f"state_fertility_means_add = {P.FAMILY_LIMITATION_MEANS:g}", body)
        self.assertIn("add_modifier = { name = te_demog_family_limitation }", _text(HISTORY))


class TestFamilyLimitationScript(unittest.TestCase):
    """te_demog_phase3_game_start / _yearly on a country against the model."""

    def _target(self, eng):
        return eng.value(eng._tree(eng.values, "te_demog_fl_target"))

    def test_the_target_matches_the_model(self):
        for laws, agr, lit, undivided in (({"law_equal_inheritance", "law_freedom_of_conscience"}, 0.74, 0.32, False),
                                          ({"law_equal_inheritance"}, 0.6, 0.9, True),
                                          ({"law_state_religion", "law_partible"}, 0.5, 0.95, False),
                                          ({"law_people_of_the_book"}, 0.5, 0.95, False),
                                          ({"law_total_separation"}, 0.2, 1.0, False),
                                          ({"law_state_atheism"}, 0.2, 0.85, False)):
            eng = _country(agr=agr, lit=lit, laws=laws, undivided=undivided)
            with self.subTest(laws=sorted(laws), lit=lit):
                self.assertAlmostEqual(self._target(eng), M.fl_target(agr, lit, laws, undivided), places=9)

    def test_france_seeds_at_historys_value_and_keeps_its_line(self):
        eng = _country(laws={"law_equal_inheritance"}, history_modifier=True)
        eng.call("te_demog_phase3_game_start")
        self.assertEqual(eng.vars["te_dg_pr_fl"], P.FAMILY_LIMITATION_MEANS)
        self.assertEqual(eng.vars["te_dg_fl_line"], P.FAMILY_LIMITATION_MEANS)
        self.assertEqual(eng.removed, ["te_demog_family_limitation"])
        self.assertAlmostEqual(eng.modifiers["te_demog_family_limitation"], 1.0, msg="the same +0.6")

    def test_another_country_seeds_at_0_with_no_line(self):
        eng = _country(laws={"law_partible"})
        eng.call("te_demog_phase3_game_start")
        self.assertEqual(eng.vars["te_dg_pr_fl"], 0.0)
        self.assertEqual(eng.vars["te_dg_fl_line"], 0.0)
        self.assertNotIn("te_demog_family_limitation", eng.modifiers)

    def test_a_year_matches_the_model(self):
        neighbours = [_neighbour(3e6, 0.6), _neighbour(1e6, 0.0), _neighbour(2e6), _neighbour(5e6, 0.9, root=True)]
        for share, laws, agr, lit, ero in ((0.6, {"law_equal_inheritance"}, 0.74, 0.3, 0.0),
                                           (0.1, {"law_partible"}, 0.5, 0.9, 0.2),
                                           (0.0, {"law_partible"}, 0.5, 0.3, 0.0),
                                           (0.3, {"law_total_separation"}, 0.1, 1.0, 0.7)):
            eng = _country(agr=agr, lit=lit, ero=ero, laws=laws, share=share, neighbours=neighbours)
            eng.call("te_demog_phase3_yearly")
            # the foreign states that hold a share (the country's own and one whose owner has none are left out)
            mean = M.people_mean([(3e6, 0.6), (1e6, 0.0)])
            want = M.fl_step(share, M.fl_target(agr, lit, laws), mean)
            with self.subTest(share=share, laws=sorted(laws)):
                self.assertAlmostEqual(eng.vars["te_dg_pr_fl"], want, places=5)
                self.assertAlmostEqual(eng.vars["te_dg_fl_nb"], mean, places=5)
                line = M.fl_line(want, ero)
                self.assertAlmostEqual(eng.vars["te_dg_fl_line"], line, places=5)
                if line > 0:
                    self.assertAlmostEqual(eng.modifiers["te_demog_family_limitation"],
                                           line / P.FAMILY_LIMITATION_MEANS, places=4)
                else:
                    self.assertNotIn("te_demog_family_limitation", eng.modifiers)

    def test_no_neighbour_spreads_nothing(self):
        eng = _country(laws={"law_partible"}, share=0.2)
        eng.call("te_demog_phase3_yearly")
        self.assertEqual(eng.vars["te_dg_pr_fl"], 0.2)
        self.assertEqual(eng.vars["te_dg_fl_nb"], -1)

    def test_nothing_runs_outside_full(self):
        for game_start in (True, False):
            eng = _country(laws={"law_equal_inheritance"}, history_modifier=True)
            eng.trigger_fixtures["te_demog_effects_run"] = False
            eng.call("te_demog_phase3_game_start" if game_start else "te_demog_phase3_yearly")
            self.assertNotIn("te_dg_pr_fl", eng.vars)
            self.assertNotIn("te_dg_ch_desired", eng.vars)
            self.assertEqual(eng.modifiers, {"te_demog_family_limitation": 1.0}, "history's modifier stays as it is")
            self.assertEqual(eng.removed, [])

    def test_the_one_refresh_site(self):
        """te_demog_family_limitation is applied by history and, under Full, only by te_demog_fl_apply, on one line the
        release script comments out (scripts/release/comment_out_census_inputs.py)."""
        hits = []
        for path in (ROOT / "common").rglob("*.txt"):
            for line in _text(path).split("\n"):
                code = line.split("#", 1)[0]
                if re.search(r"add_modifier\s*=\s*\{\s*name\s*=\s*te_demog_family_limitation\b", code):
                    hits.append((path.name, code.strip()))
        self.assertEqual(sorted(hits), sorted([
            ("extra_history.txt", "add_modifier = { name = te_demog_family_limitation }"),
            ("te_demog_fl_effects.txt", "add_modifier = { name = te_demog_family_limitation multiplier = te_demog_fl_mult }"),
        ]))

    def test_the_hooks(self):
        """Seeded at game start and stepped once a census year: the yearly pulse's census, or fast mode's clock census;
        the country's sums fill inside its census walk."""
        effects = re.sub(r"#[^\n]*", "", _text(EFFECTS))
        start = _block(effects, "te_demog_country_game_start")
        self.assertLess(start.index("te_demog_country_census = yes"), start.index("te_demog_phase3_game_start = yes"))
        yearly = _block(effects, "te_demog_country_yearly")
        self.assertLess(yearly.index("te_demog_country_census = yes"), yearly.index("te_demog_phase3_yearly = yes"))
        clock = _block(re.sub(r"#[^\n]*", "", _text(FAST_EFFECTS)), "te_demog_country_clock_census")
        self.assertLess(clock.index("te_demog_country_census = yes"), clock.index("te_demog_phase3_yearly = yes"))
        census = _block(effects, "te_demog_country_census")
        for name in ("te_demog_fl_country_init", "te_demog_fl_country_add", "te_demog_fl_country_store"):
            self.assertEqual(census.count(f"{name} = yes"), 1, name)
        self.assertLess(census.index("te_dg_c_s_pm"), census.index("te_demog_fl_country_add = yes"))


class TestCulturalHegemonyDrift(unittest.TestCase):
    def test_the_model(self):
        self.assertEqual(M.ch_target(0.0, 0.4, 0.7), 1.0)
        self.assertEqual(M.ch_target(0.3, None, 0.7), 1.0)
        self.assertAlmostEqual(M.ch_target(0.3, 0.4, 0.6), 1 + P.CH_WEIGHT * 0.3 * (0.4 / 0.6 - 1))
        self.assertEqual(M.ch_target(1.0, 0.1, 0.9), 1 - P.CH_CAP)
        self.assertEqual(M.ch_target(1.0, 0.9, 0.1), 1 + P.CH_CAP)
        self.assertAlmostEqual(M.ch_drift(1.0, 0.9), 1.0 - P.CH_RATE * 0.1)
        self.assertEqual(M.ch_exposure(1.5), 1.5 / P.CH_BENCHMARK_MAX)
        self.assertEqual(M.ch_exposure(9.0), 1.0)

    def test_the_refresh_matches_the_model(self):
        for exposure, hegemon, own, ch in ((0.3, 0.4, 0.66, 1.0), (0.25, 0.45, 0.6, 0.97), (0.0, 0.4, 0.6, 0.95),
                                           (0.3, None, 0.6, 1.0), (1.0, 0.1, 0.9, 1.0)):
            eng = _country(laws={"law_partible"}, share=0.0, exposure=exposure, desired=own, ch=ch,
                           hegemon=None if hegemon is None else {"te_dg_desired": hegemon})
            eng.call("te_demog_ch_refresh")
            target = M.ch_target(exposure, hegemon, own / ch)
            with self.subTest(exposure=exposure, hegemon=hegemon, own=own, ch=ch):
                self.assertAlmostEqual(eng.vars["te_dg_ch_desired"], M.ch_drift(ch, target), places=4)

    def test_a_first_refresh_starts_at_1(self):
        eng = _country(laws={"law_partible"}, share=0.0)
        eng.call("te_demog_ch_refresh")
        self.assertEqual(eng.vars["te_dg_ch_desired"], 1.0)

    def test_the_state_stores_the_factor_and_desired_takes_it(self):
        inp = M.Inputs(sol=12, literacy=0.6, urban_share=0.4)
        for factor in (1.0, 0.95, 1.08):
            eng = _engine_for(inp, 1836, 250000.0)
            eng.fixtures["te_demog_tfr_hegemon"] = factor
            eng.call("te_demog_seed")
            want = M.fertility(M.Inputs(sol=12, literacy=0.6, urban_share=0.4, hegemon=factor),
                               eng.vars["te_dg_e0"])["desired"]
            with self.subTest(factor=factor):
                self.assertAlmostEqual(eng.vars["te_dg_desired"], want, places=4)
                if factor == 1.0:
                    self.assertNotIn("te_dg_hegemon", eng.vars)
                else:
                    self.assertEqual(eng.vars["te_dg_hegemon"], factor)

    def test_the_states_read_is_full_only(self):
        body = re.sub(r"#[^\n]*", "", _block(_text(VALUES), "te_demog_tfr_hegemon"))
        self.assertIn("te_demog_effects_run = yes", body)
        self.assertIn("owner.var:te_dg_ch_desired", body)
        self.assertIn("multiply = te_demog_hegemon_used", _block(_text(VALUES), "te_demog_desired"))

    def test_exposure_is_the_foreign_benchmark(self):
        body = _block(_text(SPREAD_VALUES), "te_demog_ch_exposure")
        for needle in ("has_journal_entry = je_cultural_hegemony", "var:ch_benchmark_applied",
                       "te_demog_k_ch_benchmark_max"):
            self.assertIn(needle, body)
        bench = (ROOT / "common" / "script_values" / "cultural_hegemony_script_values.txt").read_text(encoding="utf-8-sig")
        self.assertRegex(bench, rf"(?m)^cultural_hegemony_foreign_benchmark_max = {P.CH_BENCHMARK_MAX:g}\b")


class TestPracticeSpreadScript(unittest.TestCase):
    """The late-marriage spec 4.4, built in phase 3: one walk over the neighbouring states, then each practice's step."""

    INP = M.Inputs(sol=9.0, literacy=0.3, urban_share=0.2, laws=frozenset({"law_no_womens_rights"}))

    def _step(self, neighbours, targets):
        eng = _engine_for(self.INP, 1836, 250000.0, place=("STATE_POSEN", "region_eastern_europe"), targets=targets)
        eng.call("te_demog_seed")
        eng.neighbours = [dict(n) for n in neighbours]
        before = {p: eng.vars[f"te_dg_pr_{p}"] for p in P.PRACTICES}
        eng.call("te_demog_practices_neighbours")
        eng.call("te_demog_practices_step")
        return eng, before

    def test_the_step_closes_part_of_the_gap_to_its_neighbours(self):
        neighbours = [{"te_dg_pr_lm": 1.0, "te_dg_pr_bs": 0.0, "state_population": 3e6},
                      {"te_dg_pr_lm": 0.4, "te_dg_pr_bs": 0.2, "state_population": 1e6},
                      {"state_population": 5e6}]   # no census: left out
        targets = {"lm": 0.8, "bs": 0.0}
        eng, before = self._step(neighbours, targets)
        for p in P.PRACTICES:
            mean = M.people_mean([(n["state_population"], n[f"te_dg_pr_{p}"]) for n in neighbours[:2]])
            with self.subTest(practice=p):
                self.assertAlmostEqual(eng.vars[f"te_dg_pr_{p}"], M.practice_drift(before[p], targets[p], mean),
                                       places=5)

    def test_no_neighbour_is_phase_twos_drift(self):
        targets = {"lm": 0.8, "bs": 0.1}
        eng, before = self._step([], targets)
        for p in P.PRACTICES:
            self.assertAlmostEqual(eng.vars[f"te_dg_pr_{p}"], M.practice_drift(before[p], targets[p]), places=5)

    def test_the_walk_runs_before_the_step(self):
        body = re.sub(r"#[^\n]*", "", _block(_text(EFFECTS), "te_demog_step_begin"))
        self.assertLess(body.index("te_demog_practices_neighbours = yes"), body.index("te_demog_practices_step = yes"))
        walk = _block(_text(SPREAD_EFFECTS), "te_demog_practices_neighbours")
        self.assertEqual(walk.count("every_neighbouring_state"), 1, "one walk a step for every practice")
        self.assertIn("has_local_variable = te_dg_pr_nb_p", _block(_text(PRACTICE_EFFECTS), "te_demog_practice_step"))


class TestSelfChecks(unittest.TestCase):
    def test_family_limitation_scaled(self):
        start = _block(_text(DEBUG_EFFECTS), "te_debug_demog_fl_selfcheck_start")
        for needle in ("NOT = { has_global_variable = te_demog_fl_selfcheck_done }",
                       "NOT = { has_modifier = te_demog_family_limitation }",
                       "var:te_dg_fl_line >= te_demog_k_fl_line_min", "var:te_dg_fl_line <= 0.3",
                       "value = modifier:state_fertility_means_add", "trigger_event = { id = te_debug_demog.90 days = 7 }",
                       "TE_SELF_CHECK START family_limitation_scaled"):
            self.assertIn(needle, start)
        apply = re.sub(r"#[^\n]*", "", _block(_text(FL_EFFECTS), "te_demog_fl_apply"))
        self.assertLess(apply.index("te_debug_demog_fl_selfcheck_start = yes"),
                        apply.index("remove_modifier = te_demog_family_limitation"), "the read before the swap")
        verdict = _block(_text(DEBUG_EVENTS), "te_debug_demog.90")
        for word in ("OK", "BROKEN", "NO_VERDICT"):
            self.assertIn(f"TE_SELF_CHECK {word} family_limitation_scaled", verdict)
        self.assertIn("remove_global_variable = te_demog_fl_selfcheck_done", verdict, "a lost line re-arms")

    def test_the_neighbour_checks(self):
        nb = _block(_text(DEBUG_EFFECTS), "te_debug_demog_fl_neighbours_check")
        for word in ("OK", "BROKEN"):
            self.assertIn(f"TE_SELF_CHECK {word} fl_neighbours_read", nb)
        self.assertIn("any_neighbouring_state", nb, "armed only where the state-scope test sees a foreign neighbour")
        reads = _block(_text(DEBUG_EFFECTS), "te_debug_demog_neighbours_selfcheck")
        for word in ("OK", "BROKEN"):
            self.assertIn(f"TE_SELF_CHECK {word} neighbouring_state_reads", reads)
        for pair in (("STATE_ULSTER", "STATE_LEINSTER"), ("STATE_ULSTER", "STATE_LOWLANDS")):
            self.assertIn(pair[0], reads)
            self.assertIn(pair[1], reads)
        snap = A.load()
        self.assertIn("STATE_LEINSTER", snap["land"]["STATE_ULSTER"], "the land control is a land neighbour")
        self.assertIn("STATE_LOWLANDS", snap["strait"]["STATE_ULSTER"], "the strait is one in adjacencies.csv")

    def test_the_playtest_table_names_them(self):
        text = _text(PLAYTEST)
        for name in ("family_limitation_scaled", "fl_neighbours_read", "neighbouring_state_reads"):
            self.assertIn(f"`TE_SELF_CHECK … {name}`", text)

    def test_the_hidden_event_ids_are_in_the_reserved_range(self):
        ids = re.findall(r"^te_debug_demog\.(\d+) = \{", _text(DEBUG_EVENTS), re.M)
        self.assertIn("90", ids)
        self.assertEqual(len(ids), len(set(ids)), "no id twice")


class TestAdjacencySnapshot(unittest.TestCase):
    def test_it_is_symmetric_and_knows_the_border(self):
        snap = A.load()
        for kind in ("land", "strait"):
            for a, near in snap[kind].items():
                for b in near:
                    self.assertIn(a, snap[kind][b], (kind, a, b))
        n = A.neighbours()
        for a, b in (("STATE_WALLONIA", "STATE_FLANDERS"), ("STATE_CATALONIA", "STATE_LANGUEDOC"),
                     ("STATE_SAVOY", "STATE_WEST_SWITZERLAND"), ("STATE_PICARDY", "STATE_FRENCH_LOW_COUNTRIES")):
            self.assertIn(b, n[a])
        self.assertNotIn("STATE_LOWLANDS", A.neighbours()["STATE_ULSTER"], "straits only when asked")
        self.assertIn("STATE_LOWLANDS", A.neighbours(straits=True)["STATE_ULSTER"])

    def test_every_listed_region_is_a_mod_state_region(self):
        regions = set(A.province_regions().values())
        snap = A.load()
        for kind in ("land", "strait"):
            self.assertLessEqual(set(snap[kind]), regions, kind)


class _PS:
    """A PracticeState stand-in for the harness's replay: what demographics_fl and neighbour_map read."""

    def __init__(self, sid, tag, region, people, agr=0.6, lit=0.3, laws=(), means_add=0.0):
        self.sid, self.tag, self.state_region, self.people = sid, tag, region, people
        self.strategic_region, self.incorporated, self.stored = "region_western_europe", True, {}
        self.inp = M.Inputs(agrarian_share=agr, literacy=lit, laws=frozenset(laws), means_add=means_add)


class TestHarness(unittest.TestCase):
    ADJ = {"R_FR": {"R_BE"}, "R_BE": {"R_FR", "R_NL"}, "R_NL": {"R_BE"}}

    def _save(self):
        fra = dict(laws={"law_equal_inheritance"}, means_add=0.6)
        return [_PS("1", "FRA", "R_FR", 30e6, agr=0.74, **fra), _PS("2", "BEL", "R_BE", 4e6),
                _PS("3", "NET", "R_NL", 3e6), _PS("4", "FRA", "R_BE", 1e6, agr=0.6, **fra)]

    def test_border_states(self):
        borders = F.border_states(self._save(), self.ADJ)
        self.assertEqual(sorted(borders["FRA"]), [(3e6, "NET"), (4e6, "BEL")], "its own state in R_BE left out")
        self.assertEqual(sorted(borders["BEL"]), [(1e6, "FRA"), (3e6, "NET"), (30e6, "FRA")])

    def test_the_replay_seeds_france_and_steps_as_the_model(self):
        loaded = [(1836, self._save()), (1838, self._save())]
        out = F.replay(loaded, self.ADJ)
        self.assertEqual(out[1836]["FRA"]["share"], P.FAMILY_LIMITATION_MEANS)
        self.assertEqual(out[1836]["BEL"]["share"], 0.0)
        target = {"FRA": M.fl_target((0.74 * 30 + 0.6 * 1) / 31, 0.3, {"law_equal_inheritance"}), "BEL": 0.0,
                  "NET": 0.0}
        border = {"FRA": [(4e6, "BEL"), (3e6, "NET")], "BEL": [(1e6, "FRA"), (3e6, "NET"), (30e6, "FRA")],
                  "NET": [(4e6, "BEL"), (1e6, "FRA")]}
        share = {"FRA": P.FAMILY_LIMITATION_MEANS, "BEL": 0.0, "NET": 0.0}
        for _ in range(2):   # 1837 at 1836's conditions, then 1838's step: every country from last year's shares
            share = {t: M.fl_step(share[t], target[t], M.people_mean([(p, share[o]) for p, o in border[t]]))
                     for t in share}
        for tag in share:
            self.assertAlmostEqual(out[1838][tag]["share"], share[tag], msg=tag)

    def test_the_regional_projection_moves_births_by_each_states_ratio(self):
        save = self._save()
        loaded = [(1836, save)]
        fl = F.replay(loaded, self.ADJ)
        ratios = F.state_ratios(save, fl[1836])
        self.assertAlmostEqual(ratios["3"], 1.0, msg="no line, no cut: unchanged")
        self.assertNotAlmostEqual(ratios["1"], 1.0, msg="France: the cut folded in")
        rows = [[1836, "W/N/C/S Europe", True, [], 40.0, 30.0, 1000.0, 0.0, "FRA", "1"],
                [1836, "W/N/C/S Europe", True, [], 40.0, 30.0, 1000.0, 0.0, "NET", "3"],
                [1836, "W/N/C/S Europe", False, ["war"], 40.0, 90.0, 1000.0, 0.0, "NET", "3"]]
        proj = F.project_regions(rows, loaded, fl)
        measured, projected = proj["groups"]["W/N/C/S Europe"]
        self.assertAlmostEqual(measured, 1000 * 20 / 2000, msg="a war year is left out")
        self.assertAlmostEqual(projected, 1000 * (40 * ratios["1"] + 40 - 60) / 2000)
        self.assertEqual(proj["world"], proj["groups"]["W/N/C/S Europe"])

    def test_neighbour_map(self):
        states = self._save()
        self.assertIsNone(DP.neighbour_map(states, None))
        near = DP.neighbour_map(states, self.ADJ)
        self.assertEqual(sorted(x.sid for x in near["2"]), ["1", "3", "4"], "its region's other state too")
        self.assertEqual(sorted(x.sid for x in near["3"]), ["2", "4"])


if __name__ == "__main__":
    unittest.main()
