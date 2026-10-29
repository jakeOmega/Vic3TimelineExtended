"""Reach (2026-10-28 rework spec §7; plan 4a R2-R9, R16).

An armed country without ICBMs keeps a weekly list of the countries its
bombers reach, from its own states, its direct subjects' and its basing
hosts'. One state trigger answers every "can this state be struck" question:
ICBMs reach all, the list reaches its countries, submarines reach coasts."""

import re
import unittest

from test_nuclear_deterrence import (ORDERED_LAUNCH_CRISIS_OPTIONS, ORDERED_LAUNCH_INCIDENT_OPTIONS, ROOT, block,
                                     loc_value, option_body, read, squash, strip_comments)

EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
CRISIS_EFFECTS = ROOT / "common/scripted_effects/nuclear_crisis_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"
SGUIS = ROOT / "common/scripted_guis/nuclear_deterrence_sguis.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/nuclear_deterrence_custom_loc.txt"
NUKE = ROOT / "common/diplomatic_actions/nuke.txt"
ARTICLE = ROOT / "common/treaty_articles/125_nuclear_basing.txt"
WEAPON_EVENTS = ROOT / "events/nuclear_weapon_events.txt"
CRISIS_EVENTS = ROOT / "events/nuclear_crisis_events.txt"
INCIDENT_EVENTS = ROOT / "events/nuclear_incident_events.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/nuclear_deterrence_widget.gui"

# What a state picker does with the state it picks when it aims a warhead.
WARHEAD_PAYLOADS = ("nuclear_first_strike = yes", "nuclear_response_strike = yes",
                    "nuclear_response_response_strike = yes", "nd_salvo_aim_here = yes",
                    "save_scope_as = target_state")


def braced(text, start):
    """The body of the block whose `{` is the first one at or after start."""
    i = text.index("{", start) + 1
    depth, j = 1, i
    while depth:
        depth += text[j] == "{"
        depth -= text[j] == "}"
        j += 1
    return text[i:j - 1]


def warhead_pickers(text):
    """Every ordered_/random_scope_state that picks the state a warhead hits."""
    for m in re.finditer(r"\b(?:ordered|random)_scope_state = \{", text):
        body = braced(text, m.start())
        if any(p in body for p in WARHEAD_PAYLOADS):
            yield text.count("\n", 0, m.start()) + 1, body


class TestReachList(unittest.TestCase):

    def setUp(self):
        self.effects = strip_comments(read(EFFECTS))
        self.refresh = squash(block(self.effects, "nd_reach_refresh"))
        self.add_from = squash(block(self.effects, "nd_reach_add_from"))

    def test_rebuilt_weekly_before_the_planner(self):
        weekly = block(self.effects, "nd_weekly_update")
        self.assertLess(weekly.index("nd_reach_refresh = yes"), weekly.index("nd_plan_refresh = yes"))

    def test_rebuilt_from_scratch_and_cleared_with_icbms(self):
        self.assertIn("if = { limit = { has_variable_list = nd_reach } clear_variable_list = nd_reach }", self.refresh)
        self.assertIn("set_variable = { name = nd_reach_count value = 0 }", self.refresh)
        self.assertIn("nd_is_armed = yes NOT = { has_technology_researched = ICBMs }", self.refresh)
        self.assertLess(self.refresh.index("clear_variable_list = nd_reach"), self.refresh.index("nd_reach_add_from = yes"))

    def test_from_us_our_subjects_and_our_hosts(self):
        self.assertIn("save_scope_as = nd_reach_self", self.refresh)
        self.assertIn("every_direct_subject = { nd_reach_add_from = yes }", self.refresh)
        self.assertIn("has_type = nuclear_basing source_country = scope:nd_reach_self } target_country = {"
                      " nd_reach_add_from = yes }", self.refresh)

    def test_both_halves_never_ourselves(self):
        for needle in ("has_strategic_adjacency = scope:nd_reach_cand", "NOT = { THIS = scope:nd_reach_self }",
                       "every_country_strategic_region = { every_scope_state = {",
                       "NOT = { owner = scope:nd_reach_self }", "nd_reach_add = { KIND = adjacency }",
                       "nd_reach_add = { KIND = region }"):
            self.assertIn(needle, self.add_from)

    def test_added_once_and_counted(self):
        add = squash(block(self.effects, "nd_reach_add"))
        self.assertIn("is_target_in_variable_list = { name = nd_reach target = scope:nd_reach_new }", add)
        self.assertLess(add.index("is_target_in_variable_list"), add.index("add_to_variable_list"))
        self.assertIn("change_variable = { name = nd_reach_count add = 1 }", add)
        self.assertIn("change_variable = { name = nd_reach_$KIND$_added add = 1 }", add)
        # No edit of the list while iterating it.
        self.assertNotIn("variable = nd_reach ", self.refresh + self.add_from)

    def test_article_hooks_rebuild_the_guest(self):
        article = strip_comments(read(ARTICLE))
        for hook in ("on_entry_into_force", "on_break", "on_withdrawal"):
            body = squash(block(article, hook))
            self.assertIn("scope:article_options = { source_country = { trigger_event = { id = nuclear_weapon_events.32"
                          " days = 1 } } }", body, hook)
        event = squash(block(strip_comments(read(WEAPON_EVENTS)), "nuclear_weapon_events.32"))
        self.assertIn("hidden = yes", event)
        self.assertIn("nd_reach_refresh = yes", event)


class TestReachTriggers(unittest.TestCase):

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))

    def test_state_in_reach(self):
        body = squash(block(self.triggers, "nd_state_in_reach_of"))
        icbm = body.index("$COUNTRY$ = { has_technology_researched = ICBMs }")
        listed = body.index("is_target_in_variable_list = { name = nd_reach target = scope:nd_reach_owner }")
        coast = body.index("is_coastal = yes")
        self.assertLess(icbm, listed)
        self.assertLess(listed, coast)
        self.assertIn("has_technology_researched = advanced_submarine_technology", body)
        self.assertIn("has_variable_list = nd_reach", body)

    def test_reaches_country(self):
        # Equivalent to "any of its states is in reach", without walking them
        # all: the list holds countries, and only the coast is per state.
        body = squash(block(self.triggers, "nd_reaches_country"))
        for needle in ("has_technology_researched = ICBMs",
                       "is_target_in_variable_list = { name = nd_reach target = $TARGET$ }",
                       "has_technology_researched = advanced_submarine_technology",
                       "$TARGET$ = { any_scope_state = { is_coastal = yes } }"):
            self.assertIn(needle, body)

    def test_reach_limited(self):
        body = squash(block(self.triggers, "nd_reach_limited"))
        self.assertIn("nd_is_armed = yes", body)
        self.assertIn("NOT = { has_technology_researched = ICBMs }", body)


class TestReachReaders(unittest.TestCase):
    """Reach's readers (plan 4a R5-R7): a reach one path ignores isn't one."""

    def setUp(self):
        self.effects = strip_comments(read(EFFECTS))
        self.triggers = strip_comments(read(TRIGGERS))
        self.weapon = strip_comments(read(WEAPON_EVENTS))
        self.crisis = strip_comments(read(CRISIS_EVENTS))
        self.incident = strip_comments(read(INCIDENT_EVENTS))

    def test_every_warhead_picker_reads_reach(self):
        # The dispatchers, the salvo, the .1/.11/.24 answers, Launch on
        # Warning's fire-first and the guarantor's answer: every state a
        # warhead is aimed at is one the attacker reaches.
        found = 0
        for name, text in (("effects", self.effects), ("weapon events", self.weapon), ("crisis events", self.crisis)):
            for line, body in warhead_pickers(text):
                found += 1
                self.assertIn("nd_state_in_reach_of", block(body, "limit"), f"{name}:{line}")
        self.assertGreaterEqual(found, 25)

    def test_strike_actions_read_reach(self):
        nuke = strip_comments(read(NUKE))
        for action in ("nuke_diplo_action", "tactical_nuke_diplo_action"):
            body = block(nuke, action)
            self.assertIn("text = nd_tt_in_reach nd_reaches_country = { TARGET = scope:target_country }",
                          squash(block(body, "possible")), action)
            self.assertIn("nd_state_in_reach_of = { COUNTRY = scope:country }", block(body, "second_state_trigger"),
                          action)

    def test_every_ordered_launch_option_reads_reach(self):
        for text, options in ((self.crisis, ORDERED_LAUNCH_CRISIS_OPTIONS),
                              (self.incident, ORDERED_LAUNCH_INCIDENT_OPTIONS)):
            for option in options:
                trigger = squash(block(option_body(text, option), "trigger"))
                self.assertRegex(trigger, r"text = nd_tt_in_reach nd_reaches_country = \{ TARGET = scope:\w+ \}",
                                 option)
        guarantor = squash(block(self.crisis, "nuclear_crisis.22"))
        self.assertIn("nd_reaches_country = { TARGET = scope:attacking_country }", guarantor)

    def test_gates_read_reach(self):
        self.assertIn("nd_reaches_country = { TARGET = $ENEMY$ }", block(self.triggers, "nd_planner_candidate"))
        self.assertIn("text = nd_tt_in_reach nd_reaches_country = { TARGET = $ENEMY$ }",
                      squash(block(self.triggers, "nd_retaliation_permitted")))
        self.assertIn("nd_reaches_country = { TARGET = $ENEMY$ }", block(self.triggers, "nd_ai_nuclear_use_justified"))
        for name in ("nd_dispatch_strategic_strike", "nd_dispatch_tactical_strike"):
            body = block(self.effects, name)
            gate = squash(block(body[body.index("remove_variable = nd_dispatch_click"):], "limit"))
            self.assertIn("nd_state_in_reach_of = { COUNTRY = scope:nd_dispatching }", gate, name)

    def test_leadership_needs_the_capital_in_reach(self):
        lir = squash(block(self.triggers, "nd_leadership_in_reach"))
        self.assertIn("exists = capital capital = { nd_state_in_reach_of = { COUNTRY = scope:nd_lir_self } }", lir)
        # The mission row greys with a reason, the order refuses it, and the
        # AI never picks it.
        sgui = squash(strip_comments(read(SGUIS)))
        self.assertIn("scope:op = 76 } nd_plan_can_set_mission = { M = 3 } nd_plan_can_set_leadership = yes }", sgui)
        self.assertIn("text = nd_tt_capital_in_reach nd_leadership_in_reach = { ENEMY = scope:nd_plan_victim }",
                      squash(block(self.triggers, "nd_plan_can_set_leadership")))
        order = squash(block(self.triggers, "nd_can_order_salvo"))
        self.assertIn("text = nd_tt_capital_in_reach OR = { NOT = { var:nd_salvo_mission ?= 3 }"
                      " nd_leadership_in_reach = { ENEMY = $ENEMY$ } }", order)
        mission = squash(block(strip_comments(read(VALUES)), "nd_ai_salvo_mission_value"))
        third = mission[mission.rindex("if = {"):]
        self.assertIn("nd_leadership_in_reach = { ENEMY = scope:nd_sv_enemy }", third)
        self.assertTrue(third.endswith("value = 3 }"))
        for key in ("nd_tt_in_reach", "nd_tt_capital_in_reach"):
            self.assertTrue(loc_value(key), key)

    def test_forces_chain_ends_in_reach(self):
        pick = squash(block(self.effects, "nd_salvo_pick_target"))
        # Leadership and the Forces chain's capital step: the capital only
        # when it is in reach.
        self.assertEqual(pick.count("exists = capital capital = { nd_state_in_reach_of ="
                                    " { COUNTRY = scope:nd_salvo_attacker } }"), 2)
        self.assertNotIn(" else = {", pick)
        self.assertTrue(pick.rstrip().endswith("position = 0 nd_salvo_aim_here = yes } }"))
        # The warhead rolls only once aimed: the stockpile, the count and the
        # dice sit behind the flag.
        warhead = squash(block(self.effects, "nd_salvo_warhead"))
        aimed = warhead.index("limit = { has_variable = nd_salvo_aimed } remove_variable = nd_salvo_aimed")
        for needle in ("name = nuclear_weapon_stockpile subtract = 1", "name = nd_salvo_fired add = 1",
                       "nd_salvo_hit = yes"):
            self.assertGreater(warhead.index(needle), aimed, needle)
        self.assertIn("scope:nd_salvo_attacker = { set_variable = nd_salvo_aimed }",
                      squash(block(self.effects, "nd_salvo_aim_here")))
        self.assertIn("limit = { has_variable = nd_salvo_aimed } remove_variable = nd_salvo_aimed",
                      squash(block(self.effects, "nd_salvo_clear")))

    def test_out_of_reach_launch_flies_nothing(self):
        body = squash(block(self.effects, "nd_launch_or_intercept"))
        reach = body.index("NOT = { nd_reaches_country = { TARGET = scope:nd_strike_victim } }")
        for later in ("nd_exchange_open", "name = nd_last_launch_kind value = 1", "nuclear_incident.4"):
            self.assertLess(reach, body.index(later), later)
        branch = body[reach:body.index("else_if", reach)]
        for needle in ("name = nd_last_launch_kind value = 2", "action=out_of_reach",
                       "nd_intercepted_launch = { VICTIM = $VICTIM$ }"):
            self.assertIn(needle, branch)


class TestReasonEight(unittest.TestCase):
    """Follow-through reason 8: they can't reach us, a bluff (R9)."""

    def test_classified_after_seven_and_six(self):
        body = block(strip_comments(read(CRISIS_EFFECTS)), "nd_crisis_classify_follow_through")
        order = re.findall(r"name = nd_ft_reason value = (\d)", body)
        self.assertEqual(order[:4], ["7", "6", "8", "1"])
        eight = squash(body[:body.index("name = nd_ft_reason value = 8")])
        self.assertTrue(eight.endswith("limit = { NOT = { nd_reaches_country = { TARGET = $TARGET$ } } } set_variable = {"))

    def test_text_and_preview(self):
        self.assertIn("localization_key = nd_ft_reason_8", block(strip_comments(read(CUSTOM_LOC)), "nd_crisis_ft_reason"))
        self.assertIn("-25", loc_value("nd_ft_reason_8"))
        preview = squash(block(strip_comments(read(CRISIS_EFFECTS)), "nd_crisis_preview"))
        law = preview.index("custom_tooltip = nd_tt_open_bluff_law")
        reach = preview.index("limit = { NOT = { nd_reaches_country = { TARGET = $TARGET$ } } }"
                              " custom_tooltip = nd_tt_open_bluff_reach")
        self.assertLess(law, reach)
        self.assertLess(reach, preview.index("custom_tooltip = nd_tt_open_backed"))

    def test_ai_never_bluffs_over_reach(self):
        triggers = strip_comments(read(TRIGGERS))
        for name in ("nd_threat_backed", "nd_threat_uncertain"):
            self.assertIn("nd_reaches_country = { TARGET = $TARGET$ }", block(triggers, name), name)


class TestReachRow(unittest.TestCase):
    """The Forces section's Reach row (plan 4a R15): display only, after
    Survivors, while armed without ICBMs."""

    def setUp(self):
        self.widget = read(WIDGET)
        self.sguis = strip_comments(read(SGUIS))

    def test_row_after_survivors(self):
        survivors = self.widget.index('text = "nd_w_survivors_label"')
        reach = self.widget.index('text = "nd_w_reach_label"')
        self.assertLess(survivors, reach)
        self.assertLess(reach, self.widget.index('text = "nd_w_reliability_label"'))
        row = self.widget[self.widget.rindex("nd_row = {", 0, reach):self.widget.index('text = "nd_w_reliability_label"')]
        self.assertIn("GetScriptedGui('nd_reach_limited_sgui').IsShown(", row)
        self.assertIn('text = "nd_w_reach_value"', row)
        self.assertIn("GetScriptedGui('nd_reach_list_sgui').ExecuteTooltip(", row)
        self.assertNotIn("onclick", row)

    def test_sguis(self):
        shown = squash(block(self.sguis, "nd_reach_limited_sgui"))
        self.assertIn("is_shown = { nd_reach_limited = yes }", shown)
        self.assertIn("is_valid = { always = no }", shown)
        # One list, each host marked on its own line (gotcha #18: a heading
        # over a script-built list prints above all of it).
        listed = squash(block(self.sguis, "nd_reach_list_sgui"))
        self.assertIn("every_in_list = { variable = nd_reach if = { limit = { nd_hosts_weapons_of = { GUEST = root } }"
                      " custom_tooltip = nd_w_reach_entry_host } else = { custom_tooltip = nd_w_reach_entry } }", listed)

    def test_loc(self):
        for key in ("nd_w_reach_label", "nd_w_reach_value", "nd_w_reach_tt", "nd_w_reach_entry", "nd_w_reach_entry_host",
                    "nd_w_reach_value_bombers", "nd_w_reach_value_subs"):
            self.assertTrue(loc_value(key), key)
        self.assertIn("AddLocalizationIf(THIS.GetCountry.Exists", loc_value("nd_w_reach_entry"))

class TestReachSelfCheck(unittest.TestCase):

    def test_reach_self_check(self):
        refresh = block(strip_comments(read(EFFECTS)), "nd_reach_refresh")
        for needle in ("TE_SELF_CHECK OK nd_reach", "TE_SELF_CHECK BROKEN nd_reach",
                       "has_global_variable = nd_reach_self_check_done",
                       "Var('nd_reach_adjacency_added')", "Var('nd_reach_region_added')"):
            self.assertIn(needle, refresh)


if __name__ == "__main__":
    unittest.main()
