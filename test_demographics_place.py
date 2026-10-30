"""Demographics phase 3: the national urban pattern's effects and the Planned Capital decision
(docs/superpowers/specs/2026-10-08-demographics-design.md §5.1).

The pattern's strength and largest city through test_demographics_registry's country interpreter (the census runs
te_demog_up_country), each state's yearly refresh through its state interpreter, and static checks on the modifiers'
sizes, the decision's gates, the site event, the generated move and the wiring.
"""

import importlib.util
import re
import unittest

import test_demographics_registry as R
from test_demographics_registry import (ROOT, PLACE_EFFECTS, PLACE_TRIGGERS, PLACE_VALUES, _block, _Engine, _find,
                                        _parse_script, _text)

import demographics_effects as DE  # noqa: E402  (test_demographics_registry puts scripts/analysis on the path)

PLACE_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_place_modifiers.txt"
DECISIONS = ROOT / "common" / "decisions" / "te_demog_decisions.txt"
CAPITAL_EVENTS = ROOT / "events" / "te_demog_capital_events.txt"
DEBUG_EVENTS = ROOT / "events" / "te_debug_demog_events.txt"
GENERATED_MOVE = ROOT / "common" / "scripted_effects" / "te_demog_capital_generated.txt"
DEMOG_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_demog_on_actions.txt"
CIVIL_WAR_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_civil_war_on_actions.txt"
EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_effects.txt"
ENGINE_MODIFIERS = ROOT / "docs" / "engine" / "modifiers_summary.txt"
LOC_DIR = ROOT / "localization" / "english"

_spec = importlib.util.spec_from_file_location(
    "gen_planned_capital", ROOT / "scripts" / "generators" / "gen_planned_capital.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def _values():
    """name -> number for the constants (te_demog_k_*) in the place values."""
    return {m.group(1): float(m.group(2)) for m in
            re.finditer(r"^(te_demog_k_\w+) = \{ value = (-?[\d.]+) \}", _text(PLACE_VALUES), re.M)}


def _modifier(name):
    return {k: float(v) for k, _, v in _parse_script(_block(_text(PLACE_MODIFIERS), name)) if k != "icon"}


K = _values()


class _PlaceEngine(R._CountryEngine):
    """The country interpreter plus a state's owner = var:X (the stored country is the one running) and exists = owner,
    for te_demog_up_is_primate on each state after the census."""

    def _test(self, key, op, arg):
        if key == "owner" and isinstance(arg, str):
            return self.number(arg) is self.root_vars
        if key == "exists" and arg == "owner":
            return True
        return super()._test(key, op, arg)

    def reads_primate(self, state_vars):
        return self.holds_in(state_vars, [("te_demog_up_is_primate", "=", "yes")])


class TestStrength(unittest.TestCase):
    """te_demog_up_country, run inside the country census: the largest city, the states counted and the strength."""

    def census(self, urbans):
        states = []
        for u in urbans:
            s = dict(R.TestCountry._three[0])
            s["te_dg_urban"] = float(u) * 100_000
            states.append(s)
        eng = _PlaceEngine(states=states, fixtures={"year": 1900.0},
                           triggers={"is_ai": False, "te_demog_cohorts_run": True})
        eng.call("te_demog_country_census")
        return eng, states

    @classmethod
    def setUpClass(cls):
        R.TestCountry.setUpClass()

    def test_strength_follows_the_extended_curve(self):
        """The 2026-10-22 effects design: full at 50% primacy, then half the slope, 2 at 100%."""
        cases = (((1, 1, 1, 1), 0.0),            # 25%: the floor
                 ((2, 1, 1, 1, 1, 1, 1, 1, 1), 0.0),   # 20%, Balanced
                 ((4, 3, 3), 0.6),                     # 40%: the Primate label's floor
                 ((2, 1, 1), 1.0),                     # 50%: the reference
                 ((6, 2, 2), 1.2),                     # 60%
                 ((9, 1, 1), 0.5 + 0.5 * (9 / 11 - 0.25) / 0.25))   # 82%: past the reference at half the slope
        for urbans, want in cases:
            eng, _ = self.census(urbans)
            self.assertAlmostEqual(eng.vars["te_dg_up_s"], want, places=4, msg=urbans)
            self.assertAlmostEqual(DE.primacy(max(urbans) / sum(urbans)), want, places=4, msg=urbans)

    def test_the_largest_city_is_named_and_the_states_counted(self):
        eng, states = self.census((2, 5, 1))
        self.assertIs(eng.vars["te_dg_primate_state"], states[1])
        self.assertEqual(eng.vars["te_dg_up_states"], 3.0)
        # the flag: the largest city carries its country, and only it reads as primate
        self.assertIs(states[1]["te_dg_primate_of"], eng.root_vars)
        self.assertEqual([eng.reads_primate(s) for s in states], [False, True, False])

    def test_a_new_census_clears_the_old_flag(self):
        eng, states = self.census((2, 5, 1))
        states[0]["te_dg_urban"], states[1]["te_dg_urban"] = 900_000.0, 100_000.0
        eng.call("te_demog_country_census")
        self.assertNotIn("te_dg_primate_of", states[1])
        self.assertEqual([eng.reads_primate(s) for s in states], [True, False, False])

    def test_a_flag_naming_another_country_reads_no(self):
        """A state that changed hands keeps its old owner's flag until its new owner's census: it never matches."""
        eng, states = self.census((2, 5, 1))
        states[0]["te_dg_primate_of"] = {"another": "country"}
        self.assertFalse(eng.reads_primate(states[0]))

    def test_the_flag_self_check(self):
        body = _block(_text(PLACE_EFFECTS), "te_debug_demog_up_selfcheck")
        for need in ("te_demog_effects_run = yes", "te_debug_demog_selfchecks_run = yes",
                     "NOT = { has_global_variable = te_demog_up_selfcheck_done }",
                     "var:te_dg_up_states >= te_demog_k_up_min_states", "TE_SELF_CHECK OK primate_state_flag",
                     "TE_SELF_CHECK BROKEN primate_state_flag"):
            self.assertIn(need, body, need)
        ok = body[body.index("var:te_dg_up_chk_self = 1"):body.index("TE_SELF_CHECK OK")]
        self.assertIn("var:te_dg_up_chk_n = 1", ok, "OK needs the city read and no other state")
        self.assertIn("te_debug_demog_up_selfcheck = yes", _block(_text(PLACE_EFFECTS), "te_demog_up_country"))

    def test_fewer_than_three_states_have_no_effects(self):
        for urbans in ((5,), (5, 1)):
            eng, _ = self.census(urbans)
            self.assertEqual(eng.vars["te_dg_up_s"], 0.0, urbans)
            self.assertIn("te_dg_primate_state", eng.vars, "the panel still names the largest city")

    def test_no_urban_people_names_no_city(self):
        eng, _ = self.census((0, 0, 0))
        self.assertNotIn("te_dg_primate_state", eng.vars)
        self.assertEqual(eng.vars["te_dg_up_s"], 0.0)

    def test_the_census_calls_it_after_the_label(self):
        body = _block(_text(EFFECTS), "te_demog_country_census")
        self.assertLess(body.index("name = te_dg_urban_label value = 3"), body.index("te_demog_up_country = yes"))
        self.assertLess(body.index("te_demog_up_country = yes"), body.index("te_demog_country_lists = yes"))


class TestStateRefresh(unittest.TestCase):
    """te_demog_up_state_refresh: the modifiers' one refresh site, under Full only."""

    def run_refresh(self, full=True, primate=True, strength=0.5, census=True, held=()):
        eng = _Engine({"te_demog_up_owner_strength": strength},
                      triggers={"te_demog_effects_run": full, "te_demog_up_is_primate": primate})
        if census:
            eng.vars["te_dg_year"] = 1900.0
        for name in held:
            eng.modifiers[name] = 0.3
        eng.call("te_demog_up_state_refresh")
        return eng

    def test_the_primate_state_takes_primate_city(self):
        eng = self.run_refresh()
        self.assertEqual(eng.modifiers, {"te_demog_primate_city": 0.5})
        self.assertEqual(eng.vars["te_dg_up_mult"], 0.5)

    def test_every_other_state_takes_provincial_neglect(self):
        eng = self.run_refresh(primate=False, strength=0.8)
        self.assertEqual(eng.modifiers, {"te_demog_provincial_neglect": 0.8})

    def test_the_old_modifier_comes_off_first(self):
        eng = self.run_refresh(primate=False, held=("te_demog_primate_city",))
        self.assertEqual(eng.modifiers, {"te_demog_provincial_neglect": 0.5})
        self.assertEqual(eng.removed, ["te_demog_primate_city"])

    def test_nothing_outside_full(self):
        """Display only and Disabled: no modifier, and one left from before comes off (nothing changes outside Full)."""
        eng = self.run_refresh(full=False, held=("te_demog_primate_city", "te_demog_provincial_neglect"))
        self.assertEqual(eng.modifiers, {})

    def test_nothing_below_one_percent_strength_or_without_a_census(self):
        for kw in ({"strength": 0.0}, {"strength": 0.009}, {"census": False}):
            self.assertEqual(self.run_refresh(**kw).modifiers, {}, kw)

    def test_the_multiplier_variable_is_never_removed(self):
        """A modifier's multiplier is read again after it is applied (scripting_best_practices.md)."""
        self.assertNotIn("remove_variable = te_dg_up_mult", _text(PLACE_EFFECTS))

    def test_it_runs_from_the_state_pulse_after_the_census(self):
        hook = _block(_text(DEMOG_ON_ACTIONS), "te_demog_state_yearly_on_action")
        self.assertLess(hook.index("te_demog_state_yearly = yes"), hook.index("te_demog_up_state_refresh = yes"))
        # one refresh site for each modifier
        for name in ("te_demog_primate_city", "te_demog_provincial_neglect"):
            sites = [p for p in (ROOT / "common").rglob("*.txt") if f"name = {name}" in _text(p)]
            self.assertEqual(sites, [PLACE_EFFECTS], name)


class TestPlannedCapitalCheck(unittest.TestCase):
    def test_the_development_ends_once_the_state_is_no_longer_the_capital(self):
        for capital, want in ((True, {"te_demog_pc_new_capital": 1.0}), (False, {})):
            eng = _Engine({}, triggers={"is_capital": capital})
            eng.modifiers["te_demog_pc_new_capital"] = 1.0
            eng.call("te_demog_pc_state_check")
            self.assertEqual(eng.modifiers, want, capital)
        hook = _block(_text(DEMOG_ON_ACTIONS), "te_demog_state_yearly_on_action")
        self.assertIn("te_demog_pc_state_check = yes", hook)


class TestModifiers(unittest.TestCase):
    def test_the_fields_are_the_values(self):
        self.assertEqual(_modifier("te_demog_primate_city"), {
            "building_urban_center_throughput_add": K["te_demog_k_up_uc"],
            "state_migration_pull_mult": K["te_demog_k_up_pull"],
            "building_university_throughput_add": K["te_demog_k_up_university"]})
        self.assertEqual(_modifier("te_demog_provincial_neglect"), {
            "state_migration_pull_mult": K["te_demog_k_up_rest_pull"],
            "state_turmoil_effects_mult": K["te_demog_k_up_rest_turmoil"],
            "state_pop_support_movement_cultural_minority_mult": K["te_demog_k_up_rest_minority"]})
        for name in ("te_demog_primate_city", "te_demog_provincial_neglect"):
            self.assertEqual(_modifier(name), DE.SIZES[name], name)
        self.assertEqual(_modifier("te_demog_pc_works"), {"country_authority_cost_add": K["te_demog_k_pc_authority"]})

    def test_every_field_is_an_engine_modifier(self):
        known = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        for name in ("te_demog_primate_city", "te_demog_provincial_neglect", "te_demog_pc_works",
                     "te_demog_pc_new_capital"):
            for field in _modifier(name):
                self.assertIn(field, known, f"{name}: {field}")

    def test_every_effect_is_at_most_a_quarter(self):
        """The 2026-10-22 effects design: a strong condition is worth one vanilla law (monument rewards give Urban
        Center throughput +25%)."""
        for name in ("te_demog_primate_city", "te_demog_provincial_neglect"):
            for field, size in _modifier(name).items():
                self.assertLessEqual(abs(size), 0.25, f"{name}: {field}")

    def test_the_timed_modifiers_run_in_days(self):
        """Literal days: add_modifier read the named { value = N } script values it once had as 0 ("for 0 days")."""
        effects = _text(PLACE_EFFECTS)
        self.assertNotRegex(effects, r"\bmonths = ")
        days = {name: int(n) for name, n in
                re.findall(r"name = (\w+)\s+days = (\d+)", _block(effects, "te_demog_pc_build"))}
        self.assertEqual(days, {"te_demog_pc_works": K["te_demog_k_pc_build_years"] * 365,
                                "te_demog_pc_new_capital": 20 * 365})

    def test_the_constants_parse_as_engine_literals(self):
        for name, v in K.items():
            self.assertLessEqual(len(repr(v).split(".")[-1]), 5, name)


class TestDecision(unittest.TestCase):
    def setUp(self):
        self.body = _block(_text(DECISIONS), "te_decision_plan_new_capital")

    def test_full_only(self):
        shown = self.body[self.body.index("is_shown = {"):self.body.index("possible = {")]
        self.assertIn("te_demog_effects_run = yes", shown)
        self.assertNotIn("has_game_rule", self.body)

    def test_the_gates(self):
        possible = self.body[self.body.index("possible = {"):self.body.index("when_taken")]
        for gate in ("var:te_dg_urban_label <= 1", "is_at_war = no", "is_diplomatic_play_committed_participant = no",
                     "NOT = { has_modifier = moved_capital_recently }",
                     "te_demog_pc_years_since >= te_demog_k_pc_cooldown_years",
                     "authority >= te_demog_k_pc_authority", "te_demog_pc_candidate = yes",
                     "has_technology_researched = steel_frame_buildings"):
            self.assertIn(gate, possible, gate)

    def test_the_site_rules(self):
        body = _block(_text(PLACE_TRIGGERS), "te_demog_pc_candidate")
        for rule in ("is_incorporated = yes", "is_capital = no", "is_homeland_of_country_cultures = owner",
                     "NOT = { te_demog_up_is_primate = yes }", "state_population >= te_demog_pc_min_people"):
            self.assertIn(rule, body, rule)

    def test_no_is_ai_anywhere(self):
        """The AI's rule is the same conditions for everyone (spec §11.2), never an is_ai branch in an outcome."""
        for path in (DECISIONS, CAPITAL_EVENTS, PLACE_EFFECTS, PLACE_TRIGGERS, PLACE_VALUES):
            self.assertNotIn("is_ai", re.sub(r"#[^\n]*", "", _text(path)), path.name)
        self.assertIn("te_demog_pc_ai_wants = yes", self.body[self.body.index("ai_chance"):])

    def test_the_ai_rule(self):
        """A crowded Primate metropolis in a country of eight states or more, out of default, money and authority."""
        body = _block(_text(PLACE_TRIGGERS), "te_demog_pc_ai_wants")
        for rule in ("var:te_dg_up_s >= te_demog_k_pc_ai_strength", "var:te_dg_up_states >= te_demog_k_pc_ai_states",
                     "var:migration_crowding_mult_applied >= te_demog_k_pc_ai_crowding", "in_default = no",
                     "gold_reserves > te_demog_pc_money_shown", "authority > te_demog_pc_ai_authority"):
            self.assertIn(rule, body, rule)
        self.assertGreaterEqual(K["te_demog_k_pc_ai_strength"], (0.4 - K["te_demog_k_up_floor"]) / K["te_demog_k_up_span"],
                                "the AI needs a Primate pattern")
        self.assertAlmostEqual(K["te_demog_k_up_floor"] + K["te_demog_k_pc_ai_strength"] * K["te_demog_k_up_span"], 0.425,
                               msg="the AI's threshold, 42.5% primacy, didn't move with the span (below 1 the curve "
                                   "is a straight line)")
        self.assertEqual(K["te_demog_k_pc_ai_crowding"], 4.5, "Migration Crowding's ceiling, the measures' mark")
        self.assertNotIn("has_modifier = migration_crowding", body, "some crowding is on almost everywhere")

    def test_it_opens_the_site_event(self):
        self.assertIn("trigger_event = { id = te_demog_capital.1 popup = yes }", self.body)

    def test_one_site_event_at_a_time(self):
        """The marker is set as the event opens, checked in possible and cleared by every option, so closing the
        event and taking the decision again can't open a second (two moves, two charges, the bar bypassed)."""
        possible = self.body[self.body.index("possible = {"):self.body.index("when_taken")]
        self.assertIn("NOT = { has_variable = te_dg_pc_pending }", possible)
        taken = self.body[self.body.index("when_taken"):]
        self.assertRegex(taken, r"set_variable = \{ name = te_dg_pc_pending value = yes days = \d+ \}")
        days = int(re.search(r"te_dg_pc_pending value = yes days = (\d+)", taken).group(1))
        self.assertGreater(days, 90, "longer than the event's life")


class TestSiteEvent(unittest.TestCase):
    def setUp(self):
        self.event = _parse_script(_block(_text(CAPITAL_EVENTS), "te_demog_capital.1"))
        self.options = [v for k, _, v in self.event if k == "option"]

    def test_three_sites_and_not_now(self):
        self.assertEqual(len(self.options), 4)
        for n, option in enumerate(self.options[:3], 1):
            self.assertEqual(_find(option, "trigger"), [
                ("exists", "=", f"scope:te_pc_site_{n}"),
                ("te_demog_pc_site_still_open", "=", [("SITE", "=", f"te_pc_site_{n}")])])
            self.assertEqual(_find(option, "te_demog_pc_build"), [("SITE", "=", f"te_pc_site_{n}")])
            self.assertNotIn("default_option", {k for k, _, _ in option})
        immediate = _find(self.event, "immediate")
        saved = [_find(v, "save_scope_as") for k, _, v in immediate if k == "ordered_scope_state"]
        self.assertEqual(saved, ["te_pc_site_1", "te_pc_site_2", "te_pc_site_3"])

    def test_not_now_is_the_default_costs_nothing_and_the_ai_never_takes_it(self):
        """Decline is the default (event_creation_guide.md): a lapsed event moves nothing."""
        keys = {k for k, _, _ in self.options[3]}
        self.assertEqual(keys, {"name", "default_option", "custom_tooltip", "hidden_effect", "ai_chance"})
        self.assertEqual(_find(self.options[3], "hidden_effect"), [("remove_variable", "=", "te_dg_pc_pending")])
        self.assertEqual(_find(_find(self.options[3], "ai_chance"), "base"), "0")

    def test_a_site_is_checked_again_when_chosen(self):
        body = _block(_text(PLACE_TRIGGERS), "te_demog_pc_site_still_open")
        for need in ("owner = ROOT", "te_demog_pc_candidate = yes", "is_at_war = no",
                     "is_diplomatic_play_committed_participant = no",
                     "te_demog_pc_years_since >= te_demog_k_pc_cooldown_years"):
            self.assertIn(need, body, need)
        build = _block(_text(PLACE_EFFECTS), "te_demog_pc_build")
        self.assertIn("remove_variable = te_dg_pc_pending", build)

    def test_it_has_a_picture(self):
        self.assertIn("event_image", {k for k, _, _ in self.event})

    def test_the_move_waits_for_the_click(self):
        """The tooltip walk tests every limit: the move's 675 branches stay behind the click-only marker, and the
        costs stay outside it so the option's tooltip shows them."""
        build = _block(_text(PLACE_EFFECTS), "te_demog_pc_build")
        guard = build.index("limit = { has_variable = te_dg_pc_click }")
        self.assertLess(guard, build.index("te_demog_pc_set_capital = yes"))
        self.assertLess(guard, build.index("set_variable = { name = te_dg_pc_year"))
        for cost in ("add_treasury = te_demog_pc_money_cost", "name = te_demog_pc_works", "name = te_demog_pc_new_capital"):
            self.assertLess(build.index(cost), guard, cost)


class TestGeneratedMove(unittest.TestCase):
    def test_the_committed_file_is_current(self):
        self.assertEqual(_text(GENERATED_MOVE), gen.render())

    def test_every_land_region_has_its_own_branch(self):
        branches = re.findall(r"state_region = s:(STATE_\w+) \} \} set_capital = (STATE_\w+) \}", _text(GENERATED_MOVE))
        self.assertTrue(all(a == b for a, b in branches))
        self.assertEqual(sorted(a for a, _ in branches), gen.regions())
        self.assertGreater(len(branches), 600)
        self.assertNotIn("STATE_ATLANTIC", {a for a, _ in branches}, "no sea region")


class TestWiring(unittest.TestCase):
    def test_the_civil_war_repair_is_wired(self):
        self.assertIn("te_demog_pc_repair_after_civil_war = yes", _block(_text(CIVIL_WAR_ON_ACTIONS),
                                                                         "te_civil_war_on_won"))
        repair = _block(_text(PLACE_EFFECTS), "te_demog_pc_repair_after_civil_war")
        self.assertIn("te_demog_effects_run = yes", repair)
        # a ladder of literal durations, no computed one (scripting_best_practices.md)
        days = [int(d) for d in re.findall(r"name = te_demog_pc_works days = (\d+)", repair)]
        self.assertEqual(len(days), 10)
        for k, d in enumerate(days):   # five years down to half a year, a half year apart
            self.assertAlmostEqual(d, 365 * (5 - k / 2), delta=1)
        for m in re.finditer(r"\bdays = (\S+)", _text(PLACE_EFFECTS)):
            self.assertRegex(m.group(1), r"^(\d+|te_demog_k_\w+)$", "a literal or a named constant")

    def test_the_self_check_event_exists(self):
        self.assertIn("trigger_event = { id = te_debug_demog.60 days = 7 }", _text(PLACE_EFFECTS))
        body = _block(_text(DEBUG_EVENTS), "te_debug_demog.60")
        for verdict in ("TE_SELF_CHECK OK planned_capital_moved", "TE_SELF_CHECK BROKEN planned_capital_moved",
                        "TE_SELF_CHECK NO_VERDICT planned_capital_moved"):
            self.assertIn(verdict, body)
        # a capital that moved at once and was moved back within the week is no verdict, not BROKEN
        broken = body[:body.index("TE_SELF_CHECK BROKEN")]
        self.assertIn("var:te_dg_pc_chk_now = 0", broken[broken.rindex("else_if"):])

    def test_the_loc_is_there(self):
        loc = "".join(_text(p) for p in LOC_DIR.glob("*.yml"))
        keys = ["te_decision_plan_new_capital", "te_decision_plan_new_capital_desc"]
        for name in ("te_demog_primate_city", "te_demog_provincial_neglect", "te_demog_pc_works",
                     "te_demog_pc_new_capital"):
            keys += [name, f"{name}_desc"]
        keys += re.findall(r"text = (te_demog_pc_tt_\w+)", _text(DECISIONS) + _text(PLACE_EFFECTS))
        keys += re.findall(r"custom_tooltip = (te_demog_\w+)", _text(DECISIONS))
        keys += re.findall(r"(?:name|title|desc|flavor|custom_tooltip) = (te_demog_capital\.1(?:\.\w+)+)",
                           _text(CAPITAL_EVENTS))
        for key in keys:
            self.assertRegex(loc, rf"(?m)^ {re.escape(key)}:\d ", key)


if __name__ == "__main__":
    unittest.main()
