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


class TestStrength(unittest.TestCase):
    """te_demog_up_country, run inside the country census: the largest city, the states counted and the strength."""

    def census(self, urbans):
        states = []
        for u in urbans:
            s = dict(R.TestCountry._three[0])
            s["te_dg_urban"] = float(u) * 100_000
            states.append(s)
        eng = R.TestCountry.country(R.TestCountry, states)
        eng.call("te_demog_country_census")
        return eng, states

    @classmethod
    def setUpClass(cls):
        R.TestCountry.setUpClass()

    def test_strength_is_linear_from_the_dominant_floor_to_sixty_percent(self):
        cases = (((1, 1, 1, 1), 0.0),            # 25%: the floor
                 ((2, 1, 1, 1, 1, 1, 1, 1, 1), 0.0),   # 20%, Balanced
                 ((4, 3, 3), (0.4 - 0.25) / 0.35),     # 40%: the Primate label's floor
                 ((6, 2, 2), 1.0),                     # 60%
                 ((9, 1, 1), 1.0))                     # 82%: capped
        for urbans, want in cases:
            eng, _ = self.census(urbans)
            self.assertAlmostEqual(eng.vars["te_dg_up_s"], want, places=5, msg=urbans)

    def test_the_largest_city_is_named_and_the_states_counted(self):
        eng, states = self.census((2, 5, 1))
        self.assertIs(eng.vars["te_dg_primate_state"], states[1])
        self.assertEqual(eng.vars["te_dg_up_states"], 3.0)

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
            "state_migration_pull_mult": K["te_demog_k_up_pull"]})
        self.assertEqual(_modifier("te_demog_provincial_neglect"), {
            "state_migration_pull_mult": K["te_demog_k_up_rest_pull"],
            "state_turmoil_effects_mult": K["te_demog_k_up_rest_turmoil"]})
        self.assertEqual(_modifier("te_demog_pc_works"), {"country_authority_cost_add": K["te_demog_k_pc_authority"]})

    def test_every_field_is_an_engine_modifier(self):
        known = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        for name in ("te_demog_primate_city", "te_demog_provincial_neglect", "te_demog_pc_works",
                     "te_demog_pc_new_capital"):
            for field in _modifier(name):
                self.assertIn(field, known, f"{name}: {field}")

    def test_every_effect_is_small(self):
        """§5.1: every effect small (a tenth or so of a decree's)."""
        for name in ("te_demog_primate_city", "te_demog_provincial_neglect"):
            for field, size in _modifier(name).items():
                self.assertLessEqual(abs(size), 0.15, f"{name}: {field}")

    def test_the_timed_modifiers_run_in_days(self):
        self.assertEqual(K["te_demog_k_pc_works_days"], K["te_demog_k_pc_build_years"] * 365)
        self.assertEqual(K["te_demog_k_pc_new_capital_days"], 20 * 365)
        effects = _text(PLACE_EFFECTS)
        self.assertNotRegex(effects, r"\bmonths = ")
        self.assertIn("days = te_demog_k_pc_works_days", effects)
        self.assertIn("days = te_demog_k_pc_new_capital_days", effects)

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

    def test_it_opens_the_site_event(self):
        self.assertIn("trigger_event = { id = te_demog_capital.1 popup = yes }", self.body)


class TestSiteEvent(unittest.TestCase):
    def setUp(self):
        self.event = _parse_script(_block(_text(CAPITAL_EVENTS), "te_demog_capital.1"))
        self.options = [v for k, _, v in self.event if k == "option"]

    def test_three_sites_and_not_now(self):
        self.assertEqual(len(self.options), 4)
        for n, option in enumerate(self.options[:3], 1):
            self.assertEqual(_find(option, "trigger"), [("exists", "=", f"scope:te_pc_site_{n}")])
            self.assertEqual(_find(option, "te_demog_pc_build"), [("SITE", "=", f"te_pc_site_{n}")])
        immediate = _find(self.event, "immediate")
        saved = [_find(v, "save_scope_as") for k, _, v in immediate if k == "ordered_scope_state"]
        self.assertEqual(saved, ["te_pc_site_1", "te_pc_site_2", "te_pc_site_3"])

    def test_not_now_costs_nothing_and_the_ai_never_takes_it(self):
        keys = {k for k, _, _ in self.options[3]}
        self.assertEqual(keys, {"name", "custom_tooltip", "ai_chance"})
        self.assertEqual(_find(_find(self.options[3], "ai_chance"), "base"), "0")

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
        self.assertIn("days = te_demog_pc_works_days_left", repair)

    def test_the_self_check_event_exists(self):
        self.assertIn("trigger_event = { id = te_debug_demog.60 days = 7 }", _text(PLACE_EFFECTS))
        body = _block(_text(DEBUG_EVENTS), "te_debug_demog.60")
        for verdict in ("TE_SELF_CHECK OK planned_capital_moved", "TE_SELF_CHECK BROKEN planned_capital_moved",
                        "TE_SELF_CHECK NO_VERDICT planned_capital_moved"):
            self.assertIn(verdict, body)

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
