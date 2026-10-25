# -*- coding: utf-8 -*-
"""Wars of independence (decolonization_events.70-.80, 2026-10-24).

A colony that declares independence can be let go, negotiated with or fought;
a fight is a war of reconquest whose goal never self-enforces. The engine logs
nothing when a goal grows a mirror, a record outlives its war, or a deferred
legacy runs early, so the wiring is pinned here
(docs/superpowers/archive/specs/2026-10-24-colonial-criteria-and-independence-wars-design.md
§ 4; mod_systems.md § Wars of Independence).
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _read(*parts):
    return re.sub(r"#[^\n]*", "", _raw(*parts))


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _block(text, name, start=0):
    """The first ``name = { ... }`` block, at any depth."""
    m = re.compile(r"(?<![\w.:$])" + re.escape(name) + r"\s*=\s*\{").search(text, start)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _def(text, name):
    """A top-level definition (an effect, trigger, event or value), never a call site."""
    m = re.compile(r"(?m)^" + re.escape(name) + r"\s*=\s*\{").search(text)
    if m is None:
        raise AssertionError(f"{name} is not defined")
    return text[m.end():_close(text, m.end() - 1)]


EFFECTS = _read("common", "scripted_effects", "decolonization_war_effects.txt")
DECOL = _read("common", "scripted_effects", "decolonization.txt")
TRIGGERS = _read("common", "scripted_triggers", "decolonization_war_triggers.txt")
EVENTS = _read("events", "decolonization_events.txt")
PLAY = _read("common", "diplomatic_plays", "te_colonial_war_play.txt")
GOAL = _read("common", "war_goal_types", "te_colonial_reconquest.txt")
REBEL_GOAL = _read("common", "war_goal_types", "te_colonial_independence.txt")
UN_TRIGGERS = _read("common", "scripted_triggers", "un_force_triggers.txt")
UN_EFFECTS = _read("common", "scripted_effects", "un_force_effects.txt")
WAR_SUPPORT = _read("common", "script_values", "zz_te_war_support_injections.txt")
ON_ACTIONS = _read("common", "on_actions", "extra_on_actions.txt")
CIVIL_WAR = _read("common", "on_actions", "te_civil_war_on_actions.txt")
VALUES = _read("common", "script_values", "colonial_empire_values.txt")
BAR = _read("common", "scripted_progress_bars", "extra_progress_bars.txt")


def _loc_keys():
    keys = set()
    folder = os.path.join(REPO, "localization", "english")
    for name in os.listdir(folder):
        if name.endswith(".yml"):
            keys |= set(re.findall(r"(?m)^ ([\w.\-]+):\d* \"", _raw("localization", "english", name)))
    return keys


class GoalAndPlayTests(unittest.TestCase):
    def test_the_goal_never_self_enforces(self):
        goal = _def(GOAL, "te_colonial_reconquest")
        self.assertIn("kind = annex_country", goal)
        self.assertNotIn("mirrored_wargoal", goal)
        self.assertRegex(_block(goal, "infamy"), r"^\s*value = 0\s*$")
        self.assertIn("decol_iw_record_enforced = yes", _block(goal, "on_enforced"))
        for block in ("possible", "valid"):
            with self.subTest(block=block):
                body = _block(goal, block)
                self.assertIn("var:decol_iw_metropole ?= root", body)
                self.assertIn("NOT = { has_variable = decol_iw_conceded }", body)

    def test_the_play_is_script_only_and_against_our_rebels(self):
        play = _def(PLAY, "dp_te_colonial_war")
        self.assertIn("war_goal = te_colonial_reconquest", play)
        self.assertIn("selectable_in_lens = { always = no }", play)
        self.assertIn("add_infamy_for_starting_initiator_wargoals = no", play)
        self.assertIn("initiator_can_add_war_goals = no", play)
        self.assertIn("target_can_add_war_goals = no", play)
        self.assertIn("var:decol_iw_metropole ?= root", _block(play, "possible"))
        self.assertNotIn("allow_negotiated_peace = no", play)

    def test_the_rebels_goal_never_self_enforces(self):
        goal = _def(REBEL_GOAL, "te_colonial_independence")
        self.assertIn("kind = custom", goal)
        self.assertIn("contestion_type = control_all_own_states", goal)
        self.assertNotIn("mirrored_wargoal", goal)
        self.assertRegex(_block(goal, "infamy"), r"^\s*value = 0\s*$")
        self.assertIn("is_significant_demand = yes", _block(goal, "ai"))
        for block in ("possible", "valid"):
            with self.subTest(block=block):
                self.assertIn("var:decol_iw_metropole ?= scope:target_country", _block(goal, block))

    def test_the_rebels_play_is_script_only_and_against_their_metropole(self):
        play = _def(PLAY, "dp_te_independence_war")
        self.assertIn("war_goal = te_colonial_independence", play)
        self.assertIn("selectable_in_lens = { always = no }", play)
        self.assertIn("add_infamy_for_starting_initiator_wargoals = no", play)
        self.assertIn("add_infamy_for_starting_target_wargoals = no", play)
        self.assertIn("initiator_can_add_war_goals = no", play)
        self.assertIn("target_can_add_war_goals = no", play)
        self.assertIn("var:decol_iw_metropole ?= scope:target_country", _block(play, "possible"))
        self.assertNotIn("allow_negotiated_peace = no", play)

    def test_the_rebels_open_the_war_with_our_goal_as_our_demand(self):
        # The first build's play from our scope (war = yes, escalation 100)
        # never became a war in the owner's first game; the rebels open it
        # now, at dp_sepoy_mutiny's escalation, our reconquest our demand.
        opening = _def(EFFECTS, "decol_iw_open_war")
        create = _block(_block(opening, "scope:decol_iw_target"), "create_diplomatic_play")
        self.assertIn("type = dp_te_independence_war", create)
        self.assertIn("target_country = scope:decol_iw_self", create)
        self.assertIn("escalation = 80", create)
        self.assertNotIn("war = yes", create)
        self.assertNotIn("initiator", create)
        demand = _block(create, "add_war_goal")
        for line in ("holder = scope:decol_iw_self", "type = te_colonial_reconquest",
                     "target_country = scope:decol_iw_target", "primary_demand = yes"):
            with self.subTest(line=line):
                self.assertIn(line, demand)
        # A second call cannot open a second play.
        self.assertIn("NOT = { decol_iw_slot_has_play = { N = $N$ } }", opening)

    def test_a_running_play_holds_the_record(self):
        settle = _def(EFFECTS, "decol_iw_settle_slot")
        hold = settle.index("decol_iw_slot_has_play = { N = $N$ }")
        # Only before a war: the play may outlive it, and a lost war settles.
        self.assertRegex(settle, r"AND = \{\s*NOT = \{ has_variable = decol_iw_war_\$N\$ \}\s*"
                                 r"decol_iw_slot_has_play = \{ N = \$N\$ \}\s*\}")
        self.assertLess(hold, settle.index("decol_iw_end_unstarted = { N = $N$ }"))
        self.assertIn("set_variable = { name = decol_iw_pending_$N$ days = 60 }", _def(EFFECTS, "decol_iw_open_slot"))
        has_play = _def(TRIGGERS, "decol_iw_slot_has_play")
        self.assertIn("is_diplomatic_play_type = dp_te_independence_war", has_play)
        self.assertIn("is_diplomatic_play_type = dp_te_colonial_war", has_play)

    def test_the_war_start_check_tells_its_cases_apart(self):
        # Re-armed (_v2): the first build's check had already fired in a save.
        for name, reason in (("decol_iw_settle_slot", "reason=still_a_play"),
                             ("decol_iw_end_won", "reason=won_unfought"),
                             ("decol_iw_end_unstarted", "reason=no_play_no_war")):
            with self.subTest(effect=name):
                body = _def(EFFECTS, name)
                self.assertIn("te_selfcheck_decol_iw_war_started_v2", body)
                self.assertIn(reason, body)
        self.assertNotIn("has_global_variable = te_selfcheck_decol_iw_war_started }", EFFECTS)
        self.assertIn("te_selfcheck_decol_iw_play_created", _def(EFFECTS, "decol_iw_open_war"))
        # A player who backs down chooses to let them go: only an AI is read.
        self.assertIn("is_ai = yes", _def(EFFECTS, "decol_iw_end_unstarted"))

    def test_the_un_force_knows_the_rebels_play(self):
        self.assertIn("un_force_goal_strikeable = { TYPE = te_colonial_independence PLAY = dp_te_independence_war }",
                      _def(UN_TRIGGERS, "un_force_has_strikeable_goal"))
        self.assertIn("un_force_strike_goal_type = { TYPE = te_colonial_independence PLAY = dp_te_independence_war }",
                      _def(UN_EFFECTS, "un_force_strike_war_goals"))


class DeferralTests(unittest.TestCase):
    def test_a_fought_declaration_defers_the_legacy(self):
        path = _def(DECOL, "apply_decolonization_path")
        self.assertRegex(path, r"limit = \{ scope:decolonizing_parent \?= \{ has_variable = decol_iw_forming \} \}\s*"
                               r"decol_iw_rebels_formed = yes\s*\}\s*else = \{\s*decol_path_legacy = yes")
        # The contagion runs either way: the declaration is what inspires.
        self.assertIn("decol_path_contagion = yes", path)
        # .15 only for a country that is not fighting us.
        self.assertRegex(path, r"NOT = \{ scope:decolonizing_parent \?= \{ has_variable = decol_iw_forming \} \}\s*\}"
                               r"\s*trigger_event = \{ id = decolonization_events\.15 days = 7 \}")
        self.assertIn("decol_mark_former_colony", _def(DECOL, "decol_path_legacy"))

    def test_the_fight_sets_and_clears_the_flag_around_the_release(self):
        fight = _def(EFFECTS, "decol_iw_fight")
        self.assertLess(fight.index("set_variable = decol_iw_forming"), fight.index("form_decolonized_country = yes"))
        self.assertLess(fight.index("form_decolonized_country = yes"), fight.index("remove_variable = decol_iw_forming"))
        self.assertIn("trigger_event = { id = decolonization_events.71 days = 1 }", fight)

    def test_a_lost_war_is_a_bloody_exit(self):
        bloody = _def(EFFECTS, "decol_iw_aftermath_bloody")
        for line in ("decol_mark_former_colony = { OVERLORD = scope:decolonizing_parent }",
                     "name = bloody_decolonization_legacy_modifier", "value = -50",
                     "activate_law = law_type:law_autocracy", "activate_law = law_type:law_outlawed_dissent",
                     "activate_law = law_type:law_minority_rights_discrimination"):
            with self.subTest(line=line):
                self.assertIn(line, bloody)
        lost = _def(EVENTS, "decolonization_events.73")
        self.assertIn("decol_iw_aftermath_bloody = yes", lost)
        self.assertIn("trigger_event = { id = decolonization_events.15 days = 7 }", lost)


class RecordTests(unittest.TestCase):
    SLOT_VARS = None

    @classmethod
    def setUpClass(cls):
        names = set(re.findall(r"\bdecol_iw_[a-z_]+?_\$N\$", EFFECTS + TRIGGERS))
        cls.SLOT_VARS = sorted(n.replace("_$N$", "") for n in names)

    def test_every_record_variable_is_cleared(self):
        clear = _def(EFFECTS, "decol_iw_clear_slot")
        cleared = set(re.findall(r"remove_variable = (decol_iw_[a-z_]+)_\$N\$", clear))
        self.assertTrue(self.SLOT_VARS)
        self.assertEqual(sorted(set(self.SLOT_VARS) - cleared), [])

    def test_three_records_everywhere(self):
        for name in ("decol_iw_monthly", "decol_iw_start_wars", "decol_iw_count_backers", "decol_iw_open_all_talks",
                     "decol_iw_settle_won_now"):
            with self.subTest(effect=name):
                self.assertEqual(re.findall(r"N = (\d)", _def(EFFECTS, name)), ["1", "2", "3"])
        self.assertEqual(re.findall(r"decol_iw_slot_free = \{ N = (\d) \}", _def(TRIGGERS, "decol_iw_has_free_slot")),
                         ["1", "2", "3"])

    def test_the_settle_runs_whatever_the_entry(self):
        pool = _def(ON_ACTIONS, "decolonization_events_on_action")
        settle = pool.index("decol_iw_monthly = yes")
        self.assertLess(settle, pool.index("random_list"))
        self.assertIn("decol_iw_any_record = yes", pool[:settle])
        self.assertIn("decol_iw_backer_monthly = yes", pool)
        self.assertIn("decol_iw_secession_on_action", _def(CIVIL_WAR, "on_secession_start"))

    def test_a_revolution_rebuilds_the_home_front(self):
        self.assertIn("decol_iw_repair_after_civil_war = yes", _def(DECOL, "decol_repair_after_civil_war"))
        self.assertIn("decol_iw_refresh_home_front = yes", _def(EFFECTS, "decol_iw_repair_after_civil_war"))

    def test_each_modifier_has_one_refresh_site(self):
        for modifier, site in (("decol_iw_home_front_modifier", "decol_iw_refresh_home_front"),
                               ("decol_iw_fighters_modifier", "decol_iw_refresh_fighters"),
                               ("decol_iw_foreign_arms_modifier", "decol_iw_refresh_fighters")):
            with self.subTest(modifier=modifier):
                adds = re.findall(r"name = " + modifier + r"\b", EFFECTS + EVENTS)
                self.assertEqual(len(adds), 1)
                body = _def(EFFECTS, site)
                self.assertLess(body.index("remove_modifier = " + modifier), body.index("name = " + modifier))


class BarAndWarSupportTests(unittest.TestCase):
    def test_the_bar_has_the_term(self):
        self.assertIn("owner.colonial_stability_term_independence_war", BAR)
        self.assertIn("add = colonial_stability_term_independence_war",
                      _def(VALUES, "colonial_stability_drift_domestic"))
        leaf = _def(VALUES, "colonial_stability_term_independence_war")
        self.assertIn("decol_iw_bar_drain_per_war", leaf)
        self.assertNotRegex(leaf, r"multiply = -?\d")

    def test_the_war_support_lines_carry_loc(self):
        keys = _loc_keys()
        lines = re.findall(r'desc = "(WAR_SUPPORT_TE_DECOL_\w+)"', WAR_SUPPORT)
        self.assertEqual(sorted(set(lines)), ["WAR_SUPPORT_TE_DECOL_COLONIAL_WAR", "WAR_SUPPORT_TE_DECOL_CONDEMNED",
                                              "WAR_SUPPORT_TE_DECOL_FOREIGN_ARMS", "WAR_SUPPORT_TE_DECOL_INDEPENDENCE",
                                              "WAR_SUPPORT_TE_DECOL_SETTLERS"])
        for key in lines:
            with self.subTest(key=key):
                self.assertIn(key, keys)
        # No every_country in a script value run per country, per war, per beat.
        self.assertNotIn("every_country", WAR_SUPPORT)


class PanelTests(unittest.TestCase):
    def test_a_row_per_record_on_the_rebels_capital(self):
        gui = _read("gui", "journal_entry_widgets", "colonial_empire_widget.gui")
        for n in (1, 2, 3):
            with self.subTest(record=n):
                self.assertRegex(gui, r"te_ce_war_row = \{\s*blockoverride \"row_visible\" \{\s*visible = \"\[EqualTo_CFixedPoint\( "
                                      r"JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('decol_iw_disp_slot_" + str(n)
                                      + r"'\), '\(CFixedPoint\)1' \)\]\"\s*\}\s*blockoverride \"row_context\" \{\s*datacontext = "
                                      r"\"\[JournalEntry\.GetCountry\.MakeScope\.Var\('decol_iw_state_" + str(n) + r"'\)\.GetState\]\"")
        sgui = _def(_read("common", "scripted_guis", "colonial_empire_sguis.txt"), "colonial_empire_open_talks_sgui")
        self.assertIn("saved_scopes = { ce_state }", sgui)
        self.assertIn("decol_iw_state_can_open_talks = yes", _block(sgui, "is_valid"))
        self.assertIn("decol_iw_effect_open_talks = yes", _block(sgui, "effect"))
        # Talks drop our goal, which only a territory's rebels' war has.
        self.assertIn("var:decol_iw_kind_$N$ = 1", _def(TRIGGERS, "decol_iw_slot_can_open_talks"))
        self.assertIn("var:decol_iw_kind_$N$ = 1", _block(_def(EFFECTS, "decol_iw_open_talks"), "limit"))


class EventTests(unittest.TestCase):
    def test_fight_needs_a_free_record_and_nothing_else(self):
        declaration = _def(EVENTS, "decolonization_events.70")
        fight = declaration[declaration.index("name = decolonization_events.70.c"):]
        trigger = _block(fight, "trigger")
        self.assertIn("decol_iw_has_free_slot = yes", trigger)
        self.assertNotIn("authority", trigger)

    def test_intervention_is_guarded(self):
        guard = _def(TRIGGERS, "decol_iw_can_intervene")
        for line in ("is_at_war = no", "NOT = { is_in_same_power_bloc = scope:decol_iw_gp_metropole }",
                     "NOT = { has_treaty_alliance_with = { TARGET = scope:decol_iw_gp_metropole } }",
                     "NOT = { has_treaty_defensive_pact_with = { TARGET = scope:decol_iw_gp_metropole } }",
                     "NOT = { has_truce_with = scope:decol_iw_gp_metropole }",
                     "NOT = { is_subject_of = scope:decol_iw_gp_metropole }",
                     "has_diplomatic_pact = { who = scope:decol_iw_gp_metropole type = rivalry }"):
            with self.subTest(line=line):
                self.assertIn(line, guard)
        intervene = _def(EVENTS, "decolonization_events.74")
        intervene = intervene[intervene.index("name = decolonization_events.74.c"):]
        self.assertIn("decol_iw_can_intervene = yes", _block(intervene, "trigger"))

    def test_the_collapse_is_a_wave(self):
        for event in ("decolonization_events.201", "decolonization_events.204"):
            with self.subTest(event=event):
                body = _def(EVENTS, event)
                self.assertIn("decol_wave_start = yes", body)
                self.assertNotIn("form_decolonized_country", body)
                self.assertNotIn("colonial_empire_clear_path_months", body)
        self.assertIn("colonial_empire_clear_path_months = yes", _def(EFFECTS, "decol_wave_end"))
        step = _def(EFFECTS, "decol_wave_step")
        self.assertIn("trigger_event = { id = decolonization_events.77 days = 60 }", step)
        self.assertIn("order_by = decol_iw_rise_order", step)


if __name__ == "__main__":
    unittest.main()
