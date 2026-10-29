"""Reach (2026-10-28 rework spec §7; plan 4a R2-R9, R16).

An armed country without ICBMs keeps a weekly list of the countries its
bombers reach, from its own states, its direct subjects' and its basing
hosts'. One state trigger answers every "can this state be struck" question:
ICBMs reach all, the list reaches its countries, submarines reach coasts."""

import unittest

from test_nuclear_deterrence import (ROOT, block, read, squash, strip_comments)

EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
ARTICLE = ROOT / "common/treaty_articles/125_nuclear_basing.txt"
WEAPON_EVENTS = ROOT / "events/nuclear_weapon_events.txt"


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


class TestReachSelfCheck(unittest.TestCase):

    def test_reach_self_check(self):
        refresh = block(strip_comments(read(EFFECTS)), "nd_reach_refresh")
        for needle in ("TE_SELF_CHECK OK nd_reach", "TE_SELF_CHECK BROKEN nd_reach",
                       "has_global_variable = nd_reach_self_check_done",
                       "Var('nd_reach_adjacency_added')", "Var('nd_reach_region_added')"):
            self.assertIn(needle, refresh)


if __name__ == "__main__":
    unittest.main()
