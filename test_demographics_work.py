"""Demographics phase 2 step 2: the workforce, pensions and health costs
(docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §2).

The script (te_demog_work_effects.txt, te_demog_work_values.txt and the hooks in te_demog_effects.txt) run by the
census's interpreter (test_demographics_registry._Engine) against demographics_model's twins: the workforce term W with
its landing on its target, guard and one refresh site; the pension setting's ages, term, interest groups and AI; the two bills; the work
deaths' split by the census's own workers; and the wiring, the panel's gates and the self-checks' text."""

import random
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
from test_demographics_registry import (  # noqa: E402  (helpers and paths only: no TestCase)
    CONSOLE_EFFECTS, DEBUG_EVENTS, DEMOG_MODIFIERS, EFFECTS, FAST_EFFECTS, WORK_EFFECTS, WORK_VALUES,
    _block, _CountryEngine, _Engine, _engine_for, _gui_type, _raw_blocks, _text)

DEBUG_VALUES = ROOT / "common" / "script_values" / "te_debug_demog_values.txt"
SGUIS = ROOT / "common" / "scripted_guis" / "te_demog_sguis.txt"
GUI = ROOT / "gui" / "te_demographics_widgets.gui"
LAYOUT = ROOT / "gui" / "te_demographics_layout.gui"   # the two composers (issue #1029)
FIELD = f"modifier:{P.WORKING_ADULT_FIELD}"


def _state(full=True, wa=0.7, at=0.35, stepped=1.0, read=0.0, w=None, pair=None, wbase=0.25, families=(0.0, 0.0)):
    """A census state after a step: the step 1 figures, its working-adult read, W in force (w) or the moved lines' pair
    (pair, with the families that sum to it)."""
    fixtures = {FIELD: read, f"modifier:{P.WOMENS_WORK_TYPE}": families[0], f"modifier:{P.REPLACED_TYPE}": families[1]}
    eng = _Engine(fixtures, triggers={"te_demog_effects_run": full, "te_demog_cohorts_run": True})
    eng.vars.update(te_dg_year=1840.0, te_dg_stepped=stepped, te_dg_wa_share=wa, te_dg_at_work=at, te_dg_wbase=wbase)
    if w is not None:
        eng.vars["te_dg_mw"] = w
        if w > 0:
            eng.modifiers["te_demog_census_workforce_up"] = w
        elif w < 0:
            eng.modifiers["te_demog_census_workforce_down"] = -w
    if pair is not None:
        eng.vars["te_dg_ln_working_adults"] = pair
        eng.modifiers["te_demog_line_working_adults_up" if pair > 0 else "te_demog_line_working_adults_down"] = abs(pair)
    return eng


def _target(wa, at):
    """W's target: workers over people less the define's base (at, the share at work, in the game's units since
    2026-10-20, as every rate)."""
    return wa * at - P.WORKING_ADULT_BASE


class TestWorkforceTerm(unittest.TestCase):
    """§2.1: W = te_demog_wf_target - 0.25 on a fixed-sign pair, landing on its target at each census step (no ramp
    since 2026-10-20: the engine's own pull phases the change in), the 0.05 guard, no cap; one refresh site."""

    def test_it_lands_from_the_pair_it_replaces(self):
        """Women in the Fields' +0.30: W replaces the pair and lands on its target at the first step; the pair comes off;
        the lines on top (Rosen's +0.03 here) are what the read holds beyond the pair."""
        eng = _state(wa=0.75, at=0.525, read=0.33, pair=0.30, families=(0.30, 0.0))
        eng.call("te_demog_workforce_refresh")
        want = M.workforce_term(_target(0.75, 0.525), 0.03)
        self.assertAlmostEqual(want, _target(0.75, 0.525))
        self.assertAlmostEqual(eng.vars["te_dg_mw"], want, places=5)
        self.assertAlmostEqual(eng.modifiers["te_demog_census_workforce_up"], want, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_wf_rem"], 0.03, places=5)
        self.assertNotIn("te_demog_line_working_adults_up", eng.modifiers)
        self.assertNotIn("te_dg_ln_working_adults", eng.vars)

    def test_it_moves_from_the_term_in_force_to_the_target(self):
        eng = _state(wa=0.65, at=0.665, read=0.10, w=0.10)
        eng.call("te_demog_workforce_refresh")
        self.assertAlmostEqual(eng.vars["te_dg_mw"], _target(0.65, 0.665), places=5)
        self.assertAlmostEqual(eng.vars["te_dg_wf_rem"], 0.0, places=5, msg="W isn't on top of itself")

    def test_a_big_jump_in_the_target_lands_in_one_step(self):
        """A target 0.35 away (a rich state's W at -0.10 when the women's rights laws and the pension age move it to
        +0.25) is W after the next census step, both ways: no ramp spreads it over years (owner, 2026-10-20)."""
        for w, wa, at in ((-0.10, 0.70, 0.714), (0.25, 0.60, 0.25)):
            with self.subTest(w=w):
                eng = _state(wa=wa, at=at, read=w, w=w)
                eng.call("te_demog_workforce_refresh")
                self.assertGreater(abs(_target(wa, at) - w), 0.3)
                self.assertAlmostEqual(eng.vars["te_dg_mw"], _target(wa, at), places=5)
                side = "up" if _target(wa, at) > 0 else "down"
                self.assertAlmostEqual(eng.modifiers[f"te_demog_census_workforce_{side}"], abs(_target(wa, at)),
                                       places=5)

    def test_a_state_that_lost_its_modifier_goes_on_from_its_variable(self):
        """A revolution's winner keeps te_dg_mw but not the modifier: the read holds nothing of W, so the remainder
        doesn't subtract it, and W lands on its target."""
        eng = _state(wa=0.65, at=0.665, read=0.0, w=0.10)
        eng.modifiers.clear()
        eng.call("te_demog_workforce_refresh")
        self.assertAlmostEqual(eng.vars["te_dg_mw"], _target(0.65, 0.665), places=5)
        self.assertAlmostEqual(eng.vars["te_dg_wf_rem"], 0.0, places=5)
        self.assertIn("te_demog_census_workforce_up", eng.modifiers)

    def test_it_matches_the_model(self):
        rng = random.Random(902)
        for _ in range(40):
            wa, at = rng.uniform(0.4, 0.8), rng.uniform(0.21, 0.77)
            w, extra = rng.uniform(-0.2, 0.3), rng.uniform(-0.3, 0.1)
            eng = _state(wa=wa, at=at, read=w + extra, w=w if w else None)
            eng.call("te_demog_workforce_refresh")
            want = M.workforce_term(_target(wa, at), extra)
            self.assertAlmostEqual(eng.vars["te_dg_mw"], want, places=4, msg=(wa, at, w, extra))
            side = "up" if want > 0 else "down"
            self.assertAlmostEqual(eng.modifiers[f"te_demog_census_workforce_{side}"], abs(want), places=4)
            self.assertEqual(len([m for m in eng.modifiers if m.startswith("te_demog_census_workforce_")]), 1)

    def test_the_guard_raises_w_past_a_negative_line_on_top(self):
        """The lowest base (0.2) + W + the lines on top stays at 0.05: a -0.2 line on top holds W at +0.05."""
        eng = _state(wa=0.3, at=0.21, read=-0.2 + 0.06, w=0.06)
        eng.call("te_demog_workforce_refresh")
        self.assertAlmostEqual(eng.vars["te_dg_mw"], P.WF_POP_RATIO_MIN - P.POP_BASE_RATIO_MIN + 0.2, places=5)

    def test_a_seed_leaves_w_as_it_is(self):
        eng = _state(stepped=0.0, read=0.12, w=0.12)
        eng.call("te_demog_workforce_refresh")
        self.assertEqual(eng.vars["te_dg_mw"], 0.12)
        self.assertEqual(eng.modifiers, {"te_demog_census_workforce_up": 0.12})

    def test_a_first_seed_lands_nothing_and_keeps_the_pair(self):
        eng = _state(stepped=0.0, read=0.3, pair=0.3, families=(0.3, 0.0))
        eng.call("te_demog_workforce_refresh")
        self.assertNotIn("te_dg_mw", eng.vars)
        self.assertEqual(eng.modifiers, {"te_demog_line_working_adults_up": 0.3})

    def test_a_new_state_lands_from_its_regions_copy(self):
        """A conquered state or a revolution's winner's is a new state object with none of the old one's variables: it
        continues the region's W (te_dg_mw_r), at its first seed already, not from the flat lines (the review of
        2026-10-12). Each refresh writes the copy."""
        eng = _state(stepped=0.0, read=0.30, pair=0.30, families=(0.30, 0.0))
        eng.region_vars["te_dg_mw_r"] = 0.18
        eng.call("te_demog_workforce_refresh")
        self.assertAlmostEqual(eng.vars["te_dg_mw"], 0.18, places=5, msg="a seed lands it unmoved")
        self.assertEqual(set(eng.modifiers), {"te_demog_census_workforce_up"})
        eng = _state(wa=0.75, at=0.525, read=0.30, pair=0.30, families=(0.30, 0.0))
        eng.region_vars["te_dg_mw_r"] = 0.18
        eng.call("te_demog_workforce_refresh")
        self.assertAlmostEqual(eng.vars["te_dg_mw"], M.workforce_term(_target(0.75, 0.525), 0.0), places=5)
        self.assertAlmostEqual(eng.region_vars["te_dg_mw_r"], eng.vars["te_dg_mw"], places=5)

    def test_a_lost_modifier_comes_back_within_a_month(self):
        """te_demog_workforce_heal, beside the pair's own refresh in the monthly and owner-change hooks."""
        eng = _state(read=0.0, w=0.12)
        eng.modifiers.clear()
        eng.call("te_demog_workforce_heal")
        self.assertEqual(eng.modifiers, {"te_demog_census_workforce_up": 0.12})
        eng = _state(full=False, read=0.0, w=0.12)
        eng.modifiers.clear()
        eng.call("te_demog_workforce_heal")
        self.assertEqual(eng.modifiers, {}, "outside Full the census's next step clears W instead")
        on_actions = _text(ROOT / "common" / "on_actions" / "te_demog_on_actions.txt")
        self.assertIn("te_demog_workforce_heal = yes", _block(on_actions, "te_demog_lines_on_action"))
        self.assertIn("te_demog_workforce_heal = yes", _block(_text(ROOT / "events" / "te_demog_events.txt"),
                                                            "te_demog_events.4"))

    def test_outside_full_w_goes_and_the_pair_returns_that_day(self):
        eng = _state(full=False, read=0.12, w=0.12, families=(0.25, -0.03))
        eng.call("te_demog_workforce_refresh")
        self.assertNotIn("te_dg_mw", eng.vars)
        self.assertNotIn("te_dg_wf_rem", eng.vars)
        self.assertEqual(set(eng.modifiers), {"te_demog_line_working_adults_up"})
        self.assertAlmostEqual(eng.modifiers["te_demog_line_working_adults_up"], 0.22)

    def test_outside_full_with_no_term_it_changes_nothing(self):
        eng = _state(full=False, read=0.22, pair=0.22, families=(0.25, -0.03))
        eng.call("te_demog_workforce_refresh")
        self.assertEqual(eng.modifiers, {"te_demog_line_working_adults_up": 0.22})

    def test_one_refresh_site_beside_the_census_terms(self):
        """§2.1: refreshed by the census's yearly step from the state pulse (ROOT the state) and fast mode's clock step,
        beside te_demog_rates_refresh; the pair is added only in te_demog_workforce_apply."""
        for path, effect in ((EFFECTS, "te_demog_state_yearly"), (FAST_EFFECTS, "te_demog_state_clock_step")):
            body = _block(_text(path), effect)
            self.assertIn("te_demog_workforce_refresh = yes", body, effect)
            self.assertLess(body.index("te_demog_rates_refresh = yes"), body.index("te_demog_workforce_refresh = yes"))
        adds = []
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").glob("*.txt")):
            for name in ("te_demog_census_workforce_up", "te_demog_census_workforce_down"):
                if re.search(rf"add_modifier = {{ name = {name}\b", _text(path)):
                    adds.append((path.name, name))
        self.assertEqual(sorted(adds), [("te_demog_work_effects.txt", "te_demog_census_workforce_down"),
                                        ("te_demog_work_effects.txt", "te_demog_census_workforce_up")])
        self.assertIn("te_demog_census_workforce_up", _block(_text(WORK_EFFECTS), "te_demog_workforce_apply"))

    def test_the_pair_is_a_workforce_field_and_hidden(self):
        mods = _text(DEMOG_MODIFIERS)
        self.assertIn(f"{P.WORKING_ADULT_FIELD} = 1", _block(mods, "te_demog_census_workforce_up"))
        self.assertIn(f"{P.WORKING_ADULT_FIELD} = -1", _block(mods, "te_demog_census_workforce_down"))
        hidden = _block(_text(ROOT / "common" / "script_values" / "gui_chart_script_values.txt"),
                        "gui_state_hidden_modifier_count")
        panel = _text(ROOT / "gui" / "states_panel.gui")
        for name in ("te_demog_census_workforce_up", "te_demog_census_workforce_down"):
            self.assertIn(f"has_modifier = {name}", hidden)
            self.assertEqual(panel.count(f"Localize('{name}')"), 2, name)

    def test_the_remainder_check_takes_w_off_too(self):
        """Step 1's workforce_lines_net and workforce_ig_trait_type read the field less the pair: under Full W stands
        on the same field, so the remainder subtracts it as well."""
        body = _block(_text(DEBUG_VALUES), "te_debug_demog_wf_remainder")
        self.assertIn("subtract = te_demog_census_workforce_applied", body)


class TestWorkDeathSplit(unittest.TestCase):
    """§2.5: the census's own count of women among the workers at 15-64 at the last count splits work deaths, and the
    flows and Late Marriage read it too, under every setting the census runs; before a count, what the sexes' rates give
    (te_demog_women_worker_share). Until 2026-10-25 only Full split deaths by the count, and the women's-rights laws'
    share did the rest."""

    FARM = dict(sol=8, literacy=0.1, urban_share=0.05, laws=frozenset({"law_no_womens_rights",
                                                                        "law_child_labor_allowed"}))

    def _step(self, full):
        inp = M.Inputs(low_share=0.85, **self.FARM)
        eng = _engine_for(inp, 1836, 250000.0, effects={"te_demog_flows": "te_demog_no_flows = yes"})
        eng.trigger_fixtures["te_demog_effects_run"] = full
        eng.call("te_demog_seed")
        return inp, eng

    def test_the_seed_stores_the_models_share(self):
        inp, eng = self._step(full=False)
        ring = M.seed(inp, 1836, 250000.0)
        qf, qm, _ = M.group_rates(inp)
        want = M.work_figures(ring, inp, M.old_age(qf, qm))
        self.assertAlmostEqual(eng.vars["te_dg_fws_wk"], want["fws_work"], places=3)
        self.assertAlmostEqual(eng.vars["te_dg_wk_past"], want["past"], places=4)

    def test_the_step_splits_by_it_under_either_setting(self):
        for full in (True, False):
            with self.subTest(full=full):
                inp, eng = self._step(full=full)
                share = eng.vars["te_dg_fws_wk"]
                eng.fixtures.update(year=1837.0, state_population=251000.0)
                eng.call("te_demog_step_begin")
                work = eng.vars["te_dg_m_work"]
                self.assertAlmostEqual(eng.locals["te_dg_m_work_f"], work * 2 * share, places=4)
                self.assertAlmostEqual(eng.locals["te_dg_m_work_m"], work * 2 * (1 - share), places=4)
                self.assertAlmostEqual(eng.locals["te_dg_fws"], share, msg="the flows read the count too")
                # the count follows the ring, not the rates' even split (the lower strata's women work at 0.14 here)
                self.assertNotAlmostEqual(share, M.women_worker_share(inp), places=3)

    def test_before_a_count_the_rates_split(self):
        inp, eng = self._step(full=False)
        del eng.vars["te_dg_fws_wk"]
        eng.fixtures.update(year=1837.0, state_population=251000.0)
        eng.call("te_demog_step_begin")
        self.assertAlmostEqual(eng.locals["te_dg_fws"], M.women_worker_share(inp), places=6)
        self.assertAlmostEqual(eng.locals["te_dg_m_work_f"],
                               eng.vars["te_dg_m_work"] * 2 * M.women_worker_share(inp), places=4)

    def test_the_share_before_a_count_is_the_models(self):
        """te_demog_women_worker_share without a count: the sexes' rates with the participation inputs, as
        demographics_model.women_worker_share (sex_rates) gives them."""
        for mods, low in (({}, 0.0), ({}, 0.85), ({P.WOMENS_WORK_TYPE: 0.15}, 0.3), ({P.WOMENS_WORK_TYPE: 0.5}, 0.0),
                          ({P.WOMENS_WORK_TYPE: 0.2, P.PARTICIPATION_TYPE: 0.014, P.MALE_PARTICIPATION_TYPE: 0.021},
                           0.5)):
            with self.subTest(mods=mods, low=low):
                inp = M.Inputs(low_share=low, mods=dict(mods), **self.FARM)
                eng = _engine_for(inp, 1836, 250000.0)
                self.assertNotIn("te_dg_fws_wk", eng.vars)
                self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_women_worker_share")),
                                       M.women_worker_share(inp), places=9)

    def test_the_model_twin(self):
        inp = M.Inputs(laws=frozenset({"law_protected_class"}), work_female_share=0.42)
        mult = M.cause_multipliers(inp)
        f, m = M.work_split(inp, mult["work"])
        self.assertAlmostEqual(f, mult["work"] * 2 * 0.42)
        self.assertAlmostEqual(m, mult["work"] * 2 * 0.58)


class TestPensionSetting(unittest.TestCase):
    """§2.2: five positions; the fixed ages at once, the linked ones at least 65 and a year a year; a five-year term;
    the interest groups while in force; leaving Old Age Pension clears it; Full only."""

    def _country(self, full=True, oap=True, **vars_):
        # te_demog_ms_now (the year with its months) stands in for the engine's date
        eng = _Engine({"te_demog_ms_now": 1950.0}, triggers={"te_demog_effects_run": full,
                                                            "te_demog_has_pension_law": oap})
        eng.vars.update(vars_)
        return eng

    def _choose(self, eng, pos):
        eng.run([("te_demog_pension_choose", "=", [("POS", "=", pos)])])

    def test_fixed_positions_take_their_ages_at_once(self):
        for pos in ("early", "standard", "raised"):
            eng = self._country(te_dg_pension_age=65.0)
            self._choose(eng, pos)
            self.assertEqual(eng.vars["te_dg_pension_age"], P.PENSION_AGE[pos], pos)
            self.assertEqual(eng.vars["te_dg_pension_pos"], P.PENSION_POSITION_ID[pos])
            self.assertEqual(eng.vars["te_dg_pension_since"], 1950.0)  # te_demog_ms_now

    def test_linked_positions_start_at_least_at_65_and_move_a_year_a_year(self):
        eng = self._country(te_dg_pension_age=60.0, te_dg_old_age=77.0)
        self._choose(eng, "linked_average")
        self.assertEqual(eng.vars["te_dg_pension_age"], P.PENSION_LINK_FLOOR, "leaving Early raises it at once")
        for year, age in ((1951, 66.0), (1952, 67.0)):
            eng.fixtures["te_demog_ms_now"] = float(year)
            eng.call("te_demog_pension_age_refresh")
            eng.call("te_demog_pension_link_drift")
            self.assertEqual(eng.vars["te_dg_pension_age"], age)
        self.assertEqual(eng.vars["te_dg_pension_age"],
                         M.pension_position_age("linked_average", 66.0, 77.0))
        eng.vars["te_dg_old_age"] = 68.5
        eng.call("te_demog_pension_link_drift")
        self.assertEqual(eng.vars["te_dg_pension_age"], 66.0, "down a year, toward 63.5 floored at 65")

    def test_a_laws_activation_never_moves_a_linked_age(self):
        """The law hook calls te_demog_pension_age_refresh (any law of the owner's): only the yearly drift moves it."""
        eng = self._country(te_dg_pension_age=68.0, te_dg_old_age=80.0,
                            te_dg_pension_pos=float(P.PENSION_POSITION_ID["linked_common"]), te_dg_pension_since=1940.0)
        eng.call("te_demog_pension_age_refresh")
        self.assertEqual(eng.vars["te_dg_pension_age"], 68.0)
        yearly = _block(_text(EFFECTS), "te_demog_country_yearly")
        self.assertLess(yearly.index("te_demog_pension_age_refresh = yes"), yearly.index("te_demog_pension_link_drift = yes"))
        self.assertNotIn("te_demog_pension_link_drift", _text(ROOT / "common" / "on_actions" / "te_demog_on_actions.txt"))

    def test_the_term_is_five_years_to_the_month(self):
        """te_dg_pension_since holds the date to the month (te_demog_ms_now), so a position chosen in June 1950 holds
        until June 1955, not to the turn of 1955 (the review of 2026-10-12)."""
        eng = self._country()
        self.assertTrue(eng.holds([("te_demog_pension_can_change", "=", "yes")]), "none chosen yet")
        eng.fixtures["te_demog_ms_now"] = 1950.5
        self._choose(eng, "raised")
        self.assertEqual(eng.vars["te_dg_pension_since"], 1950.5)
        for now, ok in ((1950.5, False), (1955.0, False), (1955.41666, False), (1955.5, True)):
            eng.fixtures["te_demog_ms_now"] = now
            self.assertEqual(eng.holds([("te_demog_pension_can_change", "=", "yes")]), ok, now)
        eng.fixtures["te_demog_ms_now"] = 1952.5
        self.assertEqual(eng.value("te_demog_pension_term_end"), 1955.5)
        self.assertEqual(eng.value("te_demog_pension_term_left"), 3.0)
        self.assertEqual(eng.value("te_demog_pension_since_year"), 1950.0)
        self.assertEqual(eng.value("te_demog_pension_term_end_year"), 1955.0)

    def test_the_interest_groups_while_in_force(self):
        mods = _text(DEMOG_MODIFIERS)
        for pos, ig in P.PENSION_IG_APPROVAL.items():
            body = _block(mods, f"te_demog_pension_pos_{pos}")
            got = {m.group(1): int(m.group(2)) for m in
                   re.finditer(r"interest_group_(ig_\w+)_approval_add = (-?\d+)", body)}
            self.assertEqual(got, ig, pos)
            eng = self._country()
            self._choose(eng, pos)
            self.assertEqual(set(eng.modifiers), {f"te_demog_pension_pos_{pos}"})
        eng = self._country()
        self._choose(eng, "standard")
        self.assertEqual(eng.modifiers, {}, "Standard has none")

    def test_a_revolutions_winner_has_its_modifier_back_at_the_refresh(self):
        eng = self._country(te_dg_pension_pos=float(P.PENSION_POSITION_ID["early"]), te_dg_pension_since=1940.0)
        eng.call("te_demog_pension_age_refresh")
        self.assertEqual(eng.modifiers, {"te_demog_pension_pos_early": 1.0})
        self.assertEqual(eng.vars["te_dg_pension_age"], P.PENSION_AGE["early"])

    def test_leaving_old_age_pension_clears_the_setting_and_the_bill(self):
        """A repeal takes the bill off that day, not at the next yearly census (the review of 2026-10-12)."""
        eng = self._country(oap=False, te_dg_pension_age=70.0, te_dg_pension_since=1948.0,
                            te_dg_pension_pos=float(P.PENSION_POSITION_ID["raised"]), te_dg_pension_bill=1234.0)
        eng.modifiers.update(te_demog_pension_pos_raised=1.0, te_demog_pension_bill=1234.0)
        eng.call("te_demog_pension_age_refresh")
        for var in ("te_dg_pension_age", "te_dg_pension_pos", "te_dg_pension_since", "te_dg_pension_bill"):
            self.assertNotIn(var, eng.vars)
        self.assertEqual(eng.modifiers, {})
        body = _block(_text(EFFECTS), "te_demog_pension_age_refresh")
        self.assertNotIn("add_modifier", body, "never re-applied there")
        eng.trigger_fixtures["te_demog_has_pension_law"] = True
        eng.call("te_demog_pension_age_refresh")
        self.assertEqual(eng.vars["te_dg_pension_age"], P.PENSION_AGE["standard"], "a return starts at Standard")
        self.assertTrue(eng.holds([("te_demog_pension_can_change", "=", "yes")]), "with no term running")

    def test_outside_full_standard_and_nothing_else(self):
        eng = self._country(full=False, te_dg_pension_pos=float(P.PENSION_POSITION_ID["early"]),
                            te_dg_pension_since=1948.0)
        eng.call("te_demog_pension_age_refresh")
        self.assertEqual(eng.vars["te_dg_pension_age"], P.PENSION_AGE["standard"])
        self.assertNotIn("te_dg_pension_pos", eng.vars)
        self.assertEqual(eng.modifiers, {})


class TestPensionAi(unittest.TestCase):
    """§2.2, §9: the AI's yearly pulse by shared weights; is_ai only decides whom it acts for; the term binds it."""

    def _ai(self, share=0.1, debt=0.0, default=False, unemployment=0.02, old_age=74.0, ai=True, **vars_):
        fixtures = {"te_demog_ms_now": 1990.0, "te_demog_pension_bill_share": share, "scaled_debt": debt,
                    "te_demog_country_unemployment": unemployment}
        eng = _Engine(fixtures, triggers={"te_demog_effects_run": True, "te_demog_has_pension_law": True, "is_ai": ai,
                                          "in_default": default})
        eng.vars.update(te_dg_old_age=old_age, te_dg_pension_age=65.0, **vars_)
        eng.call("te_demog_pension_ai")
        return eng

    def test_a_heavy_bill_or_debt_picks_the_cheaper_positions(self):
        """Linked to Average where its age passes Raised's (80 - 5 = 75), else Raised (74 - 5 = 69)."""
        self.assertEqual(self._ai(share=0.35, old_age=80.0).vars["te_dg_pension_pos"],
                         P.PENSION_POSITION_ID["linked_average"])
        self.assertEqual(self._ai(share=0.35, old_age=74.0).vars["te_dg_pension_pos"], P.PENSION_POSITION_ID["raised"])
        self.assertEqual(self._ai(debt=0.5, old_age=74.0).vars["te_dg_pension_pos"], P.PENSION_POSITION_ID["raised"])
        self.assertEqual(self._ai(default=True).vars["te_dg_pension_pos"], P.PENSION_POSITION_ID["raised"])

    def test_unemployment_picks_early(self):
        eng = self._ai(unemployment=0.15)
        self.assertEqual(eng.vars["te_dg_pension_pos"], P.PENSION_POSITION_ID["early"])
        self.assertEqual(eng.vars["te_dg_pension_age"], P.PENSION_AGE["early"])

    def test_otherwise_it_stays_at_standard_and_starts_no_term(self):
        eng = self._ai()
        self.assertNotIn("te_dg_pension_pos", eng.vars)
        self.assertNotIn("te_dg_pension_since", eng.vars)

    def test_it_goes_back_only_once_the_reason_has_clearly_gone(self):
        """Hysteresis (the review of 2026-10-12): a cheaper position stays until the bill is under
        PENSION_AI_BILL_LOW of revenue; Early stays until unemployment is under PENSION_AI_UNEMPLOYMENT_LOW."""
        raised = dict(te_dg_pension_pos=float(P.PENSION_POSITION_ID["raised"]), te_dg_pension_since=1980.0)
        self.assertEqual(self._ai(share=0.25, **raised).vars["te_dg_pension_pos"], P.PENSION_POSITION_ID["raised"])
        self.assertEqual(self._ai(share=0.15, **raised).vars["te_dg_pension_pos"], P.PENSION_POSITION_ID["standard"])
        self.assertEqual(self._ai(share=0.15, debt=0.4, **raised).vars["te_dg_pension_pos"],
                         P.PENSION_POSITION_ID["raised"])
        early = dict(te_dg_pension_pos=float(P.PENSION_POSITION_ID["early"]), te_dg_pension_since=1980.0)
        self.assertEqual(self._ai(unemployment=0.07, **early).vars["te_dg_pension_pos"], P.PENSION_POSITION_ID["early"])
        self.assertEqual(self._ai(unemployment=0.03, **early).vars["te_dg_pension_pos"],
                         P.PENSION_POSITION_ID["standard"])

    def test_the_term_binds_it_and_a_player_is_never_moved(self):
        eng = self._ai(share=0.35, te_dg_pension_pos=float(P.PENSION_POSITION_ID["early"]), te_dg_pension_since=1988.0)
        self.assertEqual(eng.vars["te_dg_pension_pos"], P.PENSION_POSITION_ID["early"])
        self.assertNotIn("te_dg_pension_pos", self._ai(share=0.35, ai=False).vars)

    def test_it_runs_after_the_census_on_the_yearly_pulse(self):
        yearly = _block(_text(EFFECTS), "te_demog_country_yearly")
        self.assertLess(yearly.index("te_demog_country_census = yes"), yearly.index("te_demog_pension_ai = yes"))
        body = _block(_text(WORK_EFFECTS), "te_demog_pension_ai")
        self.assertEqual(body.count("is_ai"), 1, "is_ai only decides whom it acts for")


class TestCivilWarRepair(unittest.TestCase):
    """A revolution's winner has the position's interest groups and both bills back at once (the review of
    2026-10-12), from the shared civil-war layer, taking the loser's variables where it holds none."""

    def test_wired_and_complete(self):
        on_won = _block(_text(ROOT / "common" / "on_actions" / "te_civil_war_on_actions.txt"), "te_civil_war_on_won")
        self.assertIn("te_demog_pension_repair_after_civil_war = yes", on_won)
        body = _block(_text(WORK_EFFECTS), "te_demog_pension_repair_after_civil_war")
        for name in ("te_dg_pension_pos", "te_dg_pension_since", "te_dg_pension_age", "te_dg_pension_bill",
                     "te_dg_health_term"):
            self.assertIn(f"te_demog_ms_inherit = {{ NAME = {name} }}", body)
        self.assertLess(body.index("te_demog_pension_age_refresh = yes"), body.index("te_demog_bills_apply = yes"))
        self.assertIn("var:te_cw_rebels_won = 1", body)


class TestBills(unittest.TestCase):
    """§2.3 (money) and §2.4 (bureaucracy), refreshed by the country's census, Full only."""

    def _country(self, full=True, oap=True, pensioners=0.2, need=1.4, level=5, gdp=52_000_000.0, techs=0.1):
        fixtures = {"gdp": gdp, '"institution_investment_level(institution_social_security)"': float(level),
                    "te_demog_health_tech_term": techs, "income": 300_000.0}
        eng = _Engine(fixtures, triggers={"te_demog_effects_run": full, "te_demog_has_pension_law": oap})
        eng.vars.update(te_dg_pensioners=pensioners, te_dg_need=need)
        eng.call("te_demog_bills_refresh")
        return eng

    def test_the_pension_bill(self):
        eng = self._country()
        want = 52_000_000.0 / 52 * 0.2 * P.PENSION_B_PER_LEVEL * 5
        self.assertAlmostEqual(eng.vars["te_dg_pension_bill"], want, delta=1.0)
        self.assertAlmostEqual(eng.modifiers["te_demog_pension_bill"], want, delta=1.0)
        self.assertAlmostEqual(52 * want / 52_000_000.0, M.pension_bill_gdp_share(0.2, 5), places=6)
        self.assertAlmostEqual(eng.value("te_demog_pension_bill_share"), want / 300_000.0, places=4)

    def test_no_pension_bill_without_the_law_or_outside_full(self):
        for kw in (dict(oap=False), dict(full=False), dict(level=0)):
            eng = self._country(**kw)
            self.assertNotIn("te_dg_pension_bill", eng.vars, kw)
            self.assertNotIn("te_demog_pension_bill", eng.modifiers, kw)

    def test_the_health_bill_by_need_and_technology(self):
        for need, techs in ((1.4, 0.1), (1.0, 0.0), (0.9, 0.0), (4.0, 0.15)):
            eng = self._country(need=need, techs=techs)
            want = min(P.HEALTH_NEED_WEIGHT * (need - 1), P.HEALTH_NEED_CAP) + techs
            self.assertAlmostEqual(eng.vars["te_dg_health_term"], want, places=5)
            side = {1: "te_demog_health_bill_up", -1: "te_demog_health_bill_down"}
            mods = {k: v for k, v in eng.modifiers.items() if k.startswith("te_demog_health_bill_")}
            if abs(want) < 1e-9:
                self.assertEqual(mods, {})
            else:
                self.assertEqual(set(mods), {side[1 if want > 0 else -1]})
                self.assertAlmostEqual(sum(mods.values()), abs(want), places=5)
        self.assertAlmostEqual(M.health_term(1.4, frozenset({"modern_pharmaceuticals", "telemedicine"})),
                               P.HEALTH_NEED_WEIGHT * 0.4 + 2 * P.HEALTH_TECH_STEP)

    def test_the_hover_words_a_saving_as_one(self):
        """A young country's term is negative: its hover reads "costs N% less", not "costs -N% more"."""
        loc = _text(ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml")
        self.assertIn("'te_demog_wk_need_saving', 'te_demog_wk_need_bill'", loc)
        self.assertRegex(loc, r"te_demog_wk_need_saving:0 \"[^\"]*te_demog_health_term_saving[^\"]*less bureaucracy")

    def test_outside_full_both_go(self):
        eng = self._country()
        eng.trigger_fixtures["te_demog_effects_run"] = False
        eng.call("te_demog_bills_refresh")
        self.assertEqual(eng.modifiers, {})
        self.assertNotIn("te_dg_health_term", eng.vars)

    def test_the_modifiers(self):
        mods = _text(DEMOG_MODIFIERS)
        self.assertIn("country_expenses_add = 1", _block(mods, "te_demog_pension_bill"))
        self.assertIn("country_institution_cost_institution_health_system_mult = 1",
                      _block(mods, "te_demog_health_bill_up"))
        self.assertIn("country_institution_cost_institution_health_system_mult = -1",
                      _block(mods, "te_demog_health_bill_down"))
        values = _text(WORK_VALUES)
        week = _block(values, "te_demog_pension_bill_week")
        self.assertIn("value = gdp", week)
        self.assertIn("divide = 52", week, "gdp is yearly, the expense weekly")

    def test_the_census_refreshes_them_with_the_country_figures(self):
        census = _block(_text(EFFECTS), "te_demog_country_census")
        for call in ("te_demog_work_country_init = yes", "te_demog_work_country_add = yes",
                     "te_demog_work_country_store = yes"):
            self.assertEqual(census.count(call), 1, call)
        self.assertIn("te_demog_bills_refresh = yes", _block(_text(WORK_EFFECTS), "te_demog_work_country_store"))


class TestCountryFigures(unittest.TestCase):
    """The tab's figures, people-weighted over the census states (te_demog_work_country_*)."""

    def test_people_weighted(self):
        states = [dict(te_dg_year=1900.0, te_dg_people=2_000_000.0, te_dg_wa_share=0.7, te_dg_at_work=0.5,
                       te_dg_pensioners=0.1, te_dg_need=1.2, te_dg_old_age=65.0, te_dg_wk_past=0.02,
                       te_dg_wf_engine=0.26),
                  dict(te_dg_year=1900.0, te_dg_people=1_000_000.0, te_dg_wa_share=0.6, te_dg_at_work=0.8,
                       te_dg_pensioners=0.2, te_dg_need=1.5, te_dg_old_age=70.0, te_dg_wk_past=0.04,
                       te_dg_wf_engine=0.3),
                  dict(te_dg_year=1900.0, te_dg_people=5_000_000.0)]     # an old save's: no figures yet
        body = (_raw_blocks([WORK_EFFECTS])["te_demog_work_country_init"]
                + "\nevery_scope_state = { set_local_variable = { name = te_dg_c_s_pm value = { value = var:te_dg_people"
                " divide = 1000000 } } te_demog_work_country_add = yes }\n"
                + _raw_blocks([WORK_EFFECTS])["te_demog_work_country_store"])
        eng = _CountryEngine(states=states, fixtures={}, effects={"te_demog_bills_refresh": "", "te_test": body})
        eng.call("te_test")
        self.assertAlmostEqual(eng.vars["te_dg_wa_share"], (0.7 * 2 + 0.6) / 3, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_at_work"], (0.7 * 0.5 * 2 + 0.6 * 0.8) / (0.7 * 2 + 0.6), places=5)
        self.assertAlmostEqual(eng.vars["te_dg_pensioners"], (0.1 * 2 + 0.2) / 3, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_need"], (1.2 * 2 + 1.5) / 3, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_old_age"], (65 * 2 + 70) / 3, places=4)
        self.assertAlmostEqual(eng.vars["te_dg_wk_past"], (0.02 * 2 + 0.04) / 3, places=5)
        self.assertAlmostEqual(eng.vars["te_dg_wf_engine"], (0.26 * 2 + 0.3) / 3, places=5)


class TestWorkTermSelfChecks(unittest.TestCase):
    """The two engine facts §2.1 and §1.8 rest on, each a once-a-game TE_SELF_CHECK line (owner, 2026-10-12)."""

    def test_both_checks_log_both_verdicts_once_a_game(self):
        body = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_wf_term_checks")
        for name, flag in (("workforce_ratio_scale", "te_demog_selfcheck_wf_scale_done"),
                           ("workforce_follows_target", "te_demog_selfcheck_wft_done")):
            self.assertIn(f"TE_SELF_CHECK OK {name}", body)
            self.assertIn(f"TE_SELF_CHECK BROKEN {name}", body)
            self.assertIn(f"NOT = {{ has_global_variable = {flag} }}", body)
            self.assertIn(f"set_global_variable = {{ name = {flag} value = yes }}", body)

    def test_degenerate_inputs_are_excluded(self):
        body = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_wf_term_checks")
        scale, follows = body.split("workforce_follows_target", 1)[0], body
        for needle in ("NOT = { has_variable = te_dg_mw }", "var:te_dg_wf_engine > 0.01", "is_capital = yes"):
            self.assertIn(needle, scale)
        for needle in ("te_debug_demog_wft_years >= 5", "te_debug_demog_wft_moved >= te_debug_demog_wft_min_move",
                       "te_debug_demog_wft_engine_moved >= te_debug_demog_wft_half_move"):
            self.assertIn(needle, follows)
        values = _text(DEBUG_VALUES)
        self.assertIn("value = 0.03", _block(values, "te_debug_demog_wft_min_move"))
        self.assertIn("multiply = 0.5", _block(values, "te_debug_demog_wft_half_move"))
        landing = _block(_text(CONSOLE_EFFECTS), "te_debug_demog_wf_term_landing")
        self.assertIn("set_variable = { name = te_dg_wft_e0 value = var:te_dg_wf_engine }", landing)
        self.assertIn("divide = { value = te_demog_wf_set add = 1", _block(values, "te_debug_demog_wf_per_dependents"))

    def _follows(self, e0, engine, read, wbase=0.25):
        """The follows check's figures in a capital whose pops are set to wbase + read now, its engine figure engine
        now and e0 when W landed."""
        eng = _Engine({FIELD: read})
        eng.values.update(_raw_blocks([DEBUG_VALUES]))
        eng.vars.update(te_dg_wbase=wbase, te_dg_wf_engine=engine, te_dg_wft_e0=e0)
        return {name: eng.value(eng._tree(eng.values, f"te_debug_demog_wft_{name}"))
                for name in ("needed", "moved", "engine_moved", "half_move", "min_move")}

    def test_the_follows_check_asks_for_the_move_to_the_set_ratio(self):
        """2026-10-17, Braunschweig's capital: W landed from the moved lines' pair (0.039) with the engine at 0.249,
        about 0.04 below the 0.289 its pops were set to, and fell to 0.002 by 1842, the engine then at 0.252 beside a
        set ratio of 0.252. W's rule asked half of W's 0.037 fall (0.018) of a move down and read BROKEN. The move due
        was 0.003 up, under the 0.03 the check waits for: no verdict."""
        f = self._follows(e0=0.249, engine=0.252, read=0.002)
        self.assertAlmostEqual(f["needed"], 0.003)
        self.assertLess(f["moved"], f["min_move"])
        # a fast pull after a W that rose 0.04 from the engine's figure: OK
        f = self._follows(e0=0.25, engine=0.285, read=0.04)
        self.assertGreaterEqual(f["moved"], f["min_move"])
        self.assertGreaterEqual(f["engine_moved"], f["half_move"])
        # a slow pull, the same W: BROKEN
        f = self._follows(e0=0.25, engine=0.255, read=0.04)
        self.assertLess(f["engine_moved"], f["half_move"])
        # a fall the engine follows down: OK, signed the move's way
        f = self._follows(e0=0.29, engine=0.258, read=0.0)
        self.assertAlmostEqual(f["needed"], -0.04)
        self.assertGreaterEqual(f["engine_moved"], f["half_move"])

    def test_they_read_before_the_refresh_moves_anything(self):
        body = _block(_text(WORK_EFFECTS), "te_demog_workforce_refresh")
        self.assertLess(body.index("te_debug_demog_wf_term_checks = yes"), body.index("set_variable"))
        self.assertIn("te_debug_demog_wf_term_landing = yes", body)

    def test_the_console_options(self):
        events = _text(DEBUG_EVENTS)
        console = _block(events, "te_debug_demog.1")
        for option, effect in (("te_debug_demog.1.r", "te_debug_demog_wf_lines"),
                               ("te_debug_demog.1.s", "te_debug_demog_pension_term_end")):
            self.assertIn(f"name = {option}", console)
            self.assertIn(f"{effect} = yes", console)


class TestPanelGates(unittest.TestCase):
    """The Work and Retirement section reads country and state figures only under the gates that say they exist."""

    def test_the_pension_buttons(self):
        sguis = _text(SGUIS)
        for pos in P.PENSION_POSITIONS:
            body = _block(sguis, f"te_demog_pension_{pos}_sgui")
            self.assertIn("te_demog_has_pension_law = yes", body, pos)
            self.assertIn("te_demog_effects_run = yes", body, pos)
            self.assertIn("te_demog_pension_can_change = yes", body, pos)
            self.assertIn(f"te_demog_pension_choose = {{ POS = {pos} }}", body, pos)
        gui = _text(GUI)
        for pos in P.PENSION_POSITIONS:
            self.assertIn(f"GetScriptedGui('te_demog_pension_{pos}_sgui')", gui)

    def test_the_sections_exist_on_both_tabs(self):
        """The country tab's section carries the buttons; the state subtab's none (§10)."""
        gui, layout = _text(GUI), _text(LAYOUT)
        self.assertIn("te_demog_sec_work = {}", _gui_type(layout, "te_demog_tab_sections"))
        self.assertIn("te_state_demog_work = {}", _gui_type(layout, "te_state_demog_content"))
        self.assertIn("te_demog_pension_button", _gui_type(gui, "te_demog_sec_work"))
        self.assertNotIn("te_demog_pension_button", _gui_type(gui, "te_state_demog_work"))
        self.assertNotIn("GetPlayer", _gui_type(gui, "te_state_demog_work"), "the state's section reads the state")

    def test_the_rows_use_the_fixed_cells(self):
        """Rule 8: the section's rows use te_demog_figure_row's fixed cells."""
        gui = _text(GUI)
        for name in ("te_demog_sec_work", "te_state_demog_work"):
            self.assertIn("te_demog_figure_row", _gui_type(gui, name), name)


class TestWorkforceRow(unittest.TestCase):
    """The Workforce row adds up: working age x the working ages' own share at work + the workers past their end =
    te_demog_wk_share, the middle term at most 100% (an EU state in 2041 read "49% × 100% = 63%", its stored share at
    work 127% with the workers past the end counted in it)."""

    def test_working_age_times_at_work_plus_past_the_end(self):
        for wa, at, past in ((0.5, 1.274, 0.141), (0.62, 0.8, 0.02), (0.7, 0.5, 0.0), (0.4, 0.9, 0.004)):
            eng = _state(wa=wa, at=at)
            eng.vars["te_dg_wk_past"] = past
            shown = eng.value("te_demog_wk_at_work_shown")
            self.assertLessEqual(shown, 1.0, (wa, at, past))
            self.assertAlmostEqual(wa * shown + past, eng.value("te_demog_wk_share"), places=5, msg=(wa, at, past))
            self.assertEqual(eng.value("te_demog_wk_past_pct"), round(100 * past), (wa, at, past))

    def test_a_state_with_no_past_figure_yet(self):
        """An old save's state, before its first count under phase 2 step 2: no te_dg_wk_past, no third term."""
        eng = _state(wa=0.6, at=0.9)
        self.assertAlmostEqual(eng.value("te_demog_wk_at_work_shown"), 0.9, places=5)
        self.assertEqual(eng.value("te_demog_wk_past_pct"), 0)

    def test_the_loc_shows_the_third_term_only_when_there_is_one(self):
        loc = _text(ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml")
        for key, scope in (("te_demog_wk_workforce_value", "Country"), ("te_demog_st_wk_workforce_value", "State")):
            line = next(x for x in loc.splitlines() if x.startswith(f" {key}:"))
            self.assertIn("te_demog_wk_at_work_shown", line, key)
            self.assertIn(f"GreaterThan_CFixedPoint( {scope}.MakeScope.ScriptValue('te_demog_wk_past_pct'), "
                          "'(CFixedPoint)0' )", line, key)

    def test_the_pops_base(self):
        """The hover's base under the workforce term: the walk's people-weighted pop bases, else the define's."""
        self.assertAlmostEqual(_state(wbase=0.27).value("te_demog_wf_pop_base"), 0.27, places=5)
        eng = _state()
        del eng.vars["te_dg_wbase"]
        self.assertAlmostEqual(eng.value("te_demog_wf_pop_base"), P.WORKING_ADULT_BASE, places=5)


if __name__ == "__main__":
    unittest.main()
