"""Nuclear Basing (2026-10-28 rework spec §7.3, §14.6; plan 4a R10-R14).

A directed treaty article: the source (the guest) stations its weapons in the
target (the host). The guest's reach extends from the host's states, the host
counts as protected by a ready guarantor, weapons next to a country cut its
warning time, and some of the guest's weapons accidents happen on the host's
soil."""

import unittest

from test_nuclear_deterrence import (ROOT, block, loc_value, option_body, read, squash,
                                     strip_comments, tracked)

ARTICLE = ROOT / "common/treaty_articles/125_nuclear_basing.txt"
TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
MODIFIERS = ROOT / "common/static_modifiers/nuclear_deterrence_modifiers.txt"
INCIDENT_EVENTS = ROOT / "events/nuclear_incident_events.txt"
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


class TestHostAccidents(unittest.TestCase):
    """A host shares its guest's sited accidents, and their politics (spec
    §14.6, owner 2026-10-28; plan 4a R14). No custody risk: a lost warhead
    stays off the guest's stockpile."""

    def setUp(self):
        events = strip_comments(read(INCIDENT_EVENTS))
        self.accident = block(events, "nuclear_incident.30")
        self.immediate = squash(block(self.accident, "immediate"))
        self.host = block(events, "nuclear_incident.31")
        self.effects = strip_comments(read(EFFECTS))

    def test_only_sited_kinds_go_abroad_a_third_of_the_time(self):
        i = self.immediate.index("nd_accident_site_abroad = yes")
        branch = self.immediate[self.immediate.rindex("if = { limit = {", 0, i):i]
        for needle in ("var:nd_accident_kind = 1", "var:nd_accident_kind = 2",
                       "nd_hosts_weapons_of = { GUEST = scope:nd_accident_guest }"):
            self.assertIn(needle, branch)
        self.assertNotIn("var:nd_accident_kind = 4", branch)
        self.assertIn("random_list = { 1 = { nd_accident_site_abroad = yes } 2 = { nd_accident_site_home = yes } }"
                      " } else = { nd_accident_site_home = yes }", self.immediate)
        # The site comes before the damage, and a lost warhead is the guest's.
        self.assertLess(self.immediate.index("nd_accident_site_home = yes"),
                        self.immediate.index("nd_accident_local_damage = yes"))
        self.assertIn("limit = { var:nd_accident_kind = 4 } nd_accident_lose_warhead = yes", self.immediate)

    def test_site_is_a_hosts_incorporated_state(self):
        abroad = squash(block(self.effects, "nd_accident_site_abroad"))
        for needle in ("nd_hosts_weapons_of = { GUEST = scope:nd_accident_guest }", "save_scope_as = nd_accident_host",
                       "random_scope_state = { limit = { is_incorporated = yes } save_scope_as = nd_accident_state }",
                       "set_variable = nd_accident_abroad"):
            self.assertIn(needle, abroad)
        home = squash(block(self.effects, "nd_accident_site_home"))
        self.assertIn("random_scope_state = { limit = { is_incorporated = yes } save_scope_as = nd_accident_state }", home)

    def test_abroad_texts(self):
        desc = squash(block(self.accident, "desc"))
        for kind, name in ((1, "bomber"), (2, "silo")):
            key = f"nuclear_incident.30.d_{name}_abroad"
            self.assertIn(f"trigger = {{ nd_accident_kind_is = {{ K = {kind} }} has_variable = nd_accident_abroad }}"
                          f" desc = {key}", desc)
            self.assertLess(desc.index(key), desc.index(f"desc = nuclear_incident.30.d_{name}_system"))
            self.assertIn("nd_accident_host", loc_value(key))
        self.assertIn("if = { limit = { has_variable = nd_accident_abroad } remove_variable = nd_accident_abroad }",
                      squash(block(self.accident, "after")))

    def test_abroad_is_neither_hidden_nor_read_as_an_attack(self):
        conceal = squash(block(option_body(self.accident, "nuclear_incident.30.e"), "trigger"))
        self.assertIn("NOT = { has_variable = nd_accident_abroad }", conceal)
        system = squash(block(block(self.effects, "nd_system_reads_attack"), "limit"))
        self.assertIn("NOT = { has_variable = nd_accident_abroad }", system)

    def test_host_hears_of_it(self):
        sent = self.immediate[self.immediate.index("limit = { has_variable = nd_accident_abroad } scope:nd_accident_host"):]
        self.assertIn("set_variable = { name = nd_host_accident_kind value = scope:nd_accident_guest.var:nd_accident_kind }",
                      sent)
        self.assertIn("trigger_event = { id = nuclear_incident.31", sent)
        self.assertIn("event_image", self.host)
        for option in ("nuclear_incident.31.a", "nuclear_incident.31.b", "nuclear_incident.31.c"):
            self.assertTrue(loc_value(option), option)
        out = squash(option_body(self.host, "nuclear_incident.31.a"))
        self.assertIn("custom_tooltip = nd_tt_basing_order_out", out)
        self.assertIn("every_scope_treaty = { limit = { any_scope_article = { has_type = nuclear_basing"
                      " source_country = scope:nd_accident_guest target_country = ROOT } } withdraw = { country = ROOT } }",
                      out)
        self.assertIn("treaty", loc_value("nd_tt_basing_order_out"))
        protest = squash(option_body(self.host, "nuclear_incident.31.b"))
        self.assertIn("change_relations = { country = scope:nd_accident_guest value = -30 }", protest)
        quiet = squash(option_body(self.host, "nuclear_incident.31.c"))
        self.assertIn("add_modifier = { name = nd_host_accident_silence", quiet)
        self.assertRegex(quiet, r"name = nd_host_accident_silence (days|months|years) = ")
        modifier = squash(block(strip_comments(read(MODIFIERS)), "nd_host_accident_silence"))
        self.assertRegex(modifier, r"country_legitimacy_base_add = -\d")
        for key in ("nuclear_incident.31.t", "nuclear_incident.31.d_bomber", "nuclear_incident.31.d_silo",
                    "nd_host_accident_silence", "nd_host_accident_silence_desc"):
            self.assertTrue(loc_value(key), key)
        self.assertIn("remove_variable = nd_host_accident_kind", squash(block(self.host, "after")))

if __name__ == "__main__":
    unittest.main()
