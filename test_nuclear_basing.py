"""Nuclear Basing (2026-10-28 rework spec §7.3, §14.6; plan 4a R10-R14).

A directed treaty article: the source (the guest) stations its weapons in the
target (the host). The guest's reach extends from the host's states, the host
counts as protected by a ready guarantor, weapons next to a country cut its
warning time, and some of the guest's weapons accidents happen on the host's
soil."""

import unittest

from test_nuclear_deterrence import (ROOT, block, loc_value, read, squash,
                                     strip_comments, tracked)

ARTICLE = ROOT / "common/treaty_articles/125_nuclear_basing.txt"
TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
ICON = ROOT / "gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_basing.dds"


class TestBasingArticle(unittest.TestCase):

    def setUp(self):
        self.article = block(strip_comments(read(ARTICLE)), "nuclear_basing")

    def test_shape(self):
        flat = squash(self.article)
        for needle in ("kind = directed", "maintenance_paid_by = source_country", "usage_limit = once_per_side",
                       'icon = "gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_basing.dds"',
                       "target_modifier = { country_treaty_leverage_generation_add ="):
            self.assertIn(needle, flat)
        self.assertTrue(ICON.exists() or tracked(ICON), "the icon has its own tracked path")

    def test_gates(self):
        possible = squash(block(self.article, "possible"))
        for needle in ("nd_is_armed = yes", "NOT = { has_war_with = ROOT }", "text = DIPLO_ACTION_RELATIONS_POOR_OR_LESS_NOT",
                       "text = nd_tt_basing_not_our_subject", "is_direct_subject_of = ROOT"):
            self.assertIn(needle, possible)
        keep = squash(self.article[self.article.index("requirement_to_maintain"):self.article.index("can_ratify")])
        self.assertIn("text = nd_tt_guarantor_armed scope:source_country = { nd_believed_armed = yes }", keep)
        self.assertIn("NOT = { has_war_with = scope:target_country }", keep)
        ratify = squash(block(self.article, "can_ratify"))
        self.assertIn("text = DUPLICATE_ARTICLE_SAME_INPUTS", ratify)
        self.assertIn("has_type = nuclear_basing source_country = scope:source_country target_country = scope:target_country",
                      ratify)
        self.assertNotIn("outguns", ratify)

    def test_effects_text_and_ai(self):
        self.assertIn("custom_tooltip_no_bullet = nuclear_basing_effects_desc", squash(block(self.article, "on_entry_into_force")))
        ai = squash(block(self.article, "ai"))
        self.assertIn("treaty_categories = { military_defense }", ai)
        # The guest's offer is cheap to evaluate: a rival next to the host,
        # not a reach computation.
        self.assertIn("any_rival_country", ai)
        self.assertNotIn("nd_reach", ai)

    def test_loc(self):
        for key in ("nuclear_basing", "nuclear_basing_desc", "nuclear_basing_article_short_desc",
                    "nuclear_basing_effects_desc", "nd_tt_basing_not_our_subject", "nd_ai_rival_near_host",
                    "nd_ai_host_holds_warheads", "nd_ai_host_taboo"):
            self.assertTrue(loc_value(key), key)


class TestBasingCover(unittest.TestCase):
    """Basing counts as a ready guarantee at full weight (R12)."""

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))

    def basing_branch(self, name):
        body = block(self.triggers, name)
        i = body.index("has_type = nuclear_basing")
        return squash(body[body.rindex("any_scope_treaty", 0, i):])

    def test_armed_guarantor(self):
        branch = self.basing_branch("nd_has_armed_guarantor_against")
        self.assertIn("target_country = scope:nd_guarantee_ben source_country = { nd_believed_armed = yes"
                      " NOT = { this = $AGAINST$ } }", branch)

    def test_ready_guarantor_without_assembled_forces(self):
        branch = self.basing_branch("nd_has_ready_guarantor_against")
        branch = branch[:branch.index("} } }") + 5]
        self.assertIn("target_country = scope:nd_guarantee_ben4", branch)
        self.assertNotIn("nd_forces_assembled", branch)

    def test_struck_host_licenses_the_guest(self):
        branch = self.basing_branch("nd_covered_country_struck_by")
        self.assertIn("has_type = nuclear_basing source_country = scope:nd_ccs_self target_country = {"
                      " has_variable = nuked_by_country var:nuked_by_country ?= $ENEMY$ }", branch)

    def test_hosts_weapons_of(self):
        body = squash(block(self.triggers, "nd_hosts_weapons_of"))
        self.assertIn("has_type = nuclear_basing", body)
        self.assertIn("source_country = $GUEST$", body)


if __name__ == "__main__":
    unittest.main()
