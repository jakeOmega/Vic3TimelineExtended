"""Counterintelligence Support: the one covert operation that works for its
target. A country lends its service to a friend, raising the friend's three
covert defences, and gets nothing back.

The registry (test_covert_op_registry.py) pins the type's fourteen-odd sites
like any other type's. This file pins what makes it different: who may run it
(a friend, one protector per ally), what it does (one target modifier through
covert_op_add_scaled_modifier), and everything it must stay out of, because
the network, Tradecraft, detection and AI machinery treats any running
operation as hostile unless told otherwise (spec
docs/superpowers/archive/specs/2026-10-16-covert-counterintel-backlash-design.md § C,
anti-goal "Counterintelligence Support quietly planting a network inside the
ally").

Run: python3 -m unittest test_covert_counterintel_support -v
"""

import re
import unittest

from test_covert_friend import action, blocks
from test_covert_op_registry import (
    EFFECTS,
    ROOT,
    TRIGGERS,
    WIDGET,
    _loc,
    _text,
    _top_level_block,
)

MODIFIERS = ROOT / "common/static_modifiers/extra_modifiers.txt"
ON_ACTIONS = ROOT / "common/on_actions/covert_warfare_on_actions.txt"
CIS = "counterintel_support"
FRIEND = "covert_is_friend = { TARGET = scope:target_country }"
HOSTILE = "covert_op_is_hostile = yes"


def scripted_effect(name):
    return _top_level_block(_text(EFFECTS), name + " = {")


def scripted_trigger(name):
    return _top_level_block(_text(TRIGGERS), name + " = {")


def _between(text, start, end):
    return text[text.index(start): text.index(end, text.index(start))]


class ActionTest(unittest.TestCase):
    def test_action_shape(self):
        a = action(CIS)
        self.assertIn("is_hostile = no", a)
        self.assertIn("requires_approval = no", a)
        self.assertIn("should_notify_third_parties = no", a)
        self.assertIn(FRIEND, blocks(a, "possible")[0])
        # The treaty gate is for hostile operations: a partner may be protected.
        self.assertNotIn("iw_no_intel_sharing_tt", a)
        self.assertIn("cost = 25", a)
        self.assertTrue(any("covert_is_friend" in b for b in blocks(a, "requirement_to_maintain")))
        self.assertTrue(any("iw_funding_level >= 1" in b for b in blocks(a, "requirement_to_maintain")))

    def test_one_protector(self):
        possible = blocks(action(CIS), "possible")[0]
        self.assertIn("iw_cis_protector", possible)
        # Another protector blocks it; a stale mark of our own does not.
        self.assertRegex(
            possible,
            r"OR = \{\s*NOT = \{ has_variable = iw_cis_protector \}\s*var:iw_cis_protector \?= ROOT\s*\}",
        )

    def test_preview_shows_the_boost_and_no_detection(self):
        accept = blocks(action(CIS), "accept_effect")[0]
        self.assertRegex(
            accept,
            r"show_as_tooltip = \{\s*scope:target_country = \{\s*"
            r"add_modifier = \{ name = covert_counterintel_support \}",
        )
        # Never rolled, never caught: no detection warning, no friend warning.
        self.assertNotIn("covert_op_detection_warning_tt", accept)
        self.assertNotIn("covert_friend_target_warning_tt", accept)
        # Its own phase line: no network head start, no exposure cost.
        self.assertIn("text = covert_counterintel_support_phase_tt", accept)
        self.assertNotIn("covert_op_phase_warning_tt", accept)
        phase = _loc()["covert_counterintel_support_phase_tt"]
        self.assertNotIn("network", phase)
        self.assertNotIn("exposed", phase)

    def test_ai(self):
        ai = blocks(action(CIS), "ai")[0]
        will = blocks(ai, "will_propose")[0]
        for needed in (FRIEND, "covert_operations_available_slots >= 1", "var:iw_funding_level >= 1",
                       "in_default = no",
                       "intelligence_capacity_total > scope:target_country.intelligence_capacity_total",
                       "covert_ai_can_spare_influence = { TYPE = covert_counterintel_support_action }",
                       "has_treaty_alliance_with = { TARGET = scope:target_country }",
                       "scope:target_country = { is_subject_of = ROOT }",
                       "is_power_bloc_leader = yes"):
            self.assertIn(needed, will, needed)
        # At most one at a time per AI country (spec § C, my call 9).
        self.assertRegex(
            will,
            r"NOT = \{\s*any_scope_diplomatic_pact = \{\s*"
            r"is_diplomatic_action_type = covert_counterintel_support_action\s*first_country = prev\s*\}\s*\}",
        )
        self.assertEqual(blocks(ai, "will_break"), ["will_break = { always = no }"])

    def test_notification_is_addressed_to_the_target(self):
        loc = _loc()
        for suffix in ("_action_action_notification_desc", "_action_action_notification_break_desc"):
            text = loc["covert_counterintel_support" + suffix]
            self.assertIn("[INITIATOR_COUNTRY.GetName]", text)
            self.assertNotRegex(text, r"\[COUNTRY\.")


class EffectTest(unittest.TestCase):
    def test_modifier_raises_all_three_defences(self):
        block = _top_level_block(_text(MODIFIERS), "covert_counterintel_support = {")
        for axis in ("economic", "military", "ideological"):
            self.assertRegex(block, r"country_covert_defense_%s_add = 8\n" % axis)
        self.assertIn("icon = gfx/interface/icons/timed_modifier_icons/", block)
        loc = _loc()
        self.assertIn("covert_counterintel_support", loc)
        self.assertIn("covert_counterintel_support_desc", loc)

    def test_applied_on_the_target_like_every_target_effect(self):
        self.assertIn(
            "covert_op_apply_target_effect = { TYPE = counterintel_support MODIFIER = covert_counterintel_support }",
            scripted_effect("covert_ops_apply_all_phase_effects"),
        )


class ExclusionTest(unittest.TestCase):
    """The protector gets nothing: no network inside the ally, no growth, no
    head start, no Tradecraft, no detection roll, no tier-2 count, and the
    AI's priority manager never escalates it."""

    def test_excluded_from_hostile_machinery(self):
        for name in ("covert_ops_roll_detection_all", "covert_nets_sync", "covert_tradecraft_monthly",
                     "covert_op_create", "covert_ai_manage_priorities"):
            self.assertIn(HOSTILE, scripted_effect(name), name)

    def test_networks_neither_ensured_nor_counted(self):
        sync = scripted_effect("covert_nets_sync")
        ensure = _between(sync, "# ---- 1. Ensure ----", "# ---- 2. Count ----")
        count = _between(sync, "# ---- 2. Count ----", "# Cultivate assets (slice 6)")
        for part, label in ((ensure, "ensure"), (count, "count")):
            walk = part[part.index("variable = iw_ops"):]
            self.assertRegex(walk, r"variable = iw_ops\s*limit = \{ %s \}" % re.escape(HOSTILE), label)

    def test_create_gives_no_head_start_and_no_network(self):
        create = scripted_effect("covert_op_create")
        branch = _between(create, "limit = { scope:iw_new_op = { %s } }" % HOSTILE, "add_to_variable_list")
        self.assertIn("iw_net_head_start_offer", branch)
        self.assertIn("covert_net_create", branch)
        # Neither runs outside the hostile branch.
        self.assertEqual(create.count("covert_net_create"), 1)
        self.assertEqual(create.count("iw_net_head_start_offer"), 1)

    def test_tradecraft_neither_gained_nor_frozen(self):
        tc = scripted_effect("covert_tradecraft_monthly")
        self.assertRegex(tc, r"variable = iw_ops\s*limit = \{ %s \}" % re.escape(HOSTILE))
        # Idle decay runs while nothing hostile runs: a protector alone is idle.
        decay = tc[tc.index("else_if = {"):]
        self.assertNotIn("covert_operations_active", decay)
        self.assertIn(HOSTILE, decay)

    def test_tier_two_count_reads_hostile_pacts_only(self):
        self.assertIn("is_hostile_covert_operation_pact = yes", scripted_effect("covert_net_refresh_intel"))
        self.assertNotIn("is_covert_operation_pact = yes", scripted_effect("covert_net_refresh_intel"))
        hostile = scripted_trigger("is_hostile_covert_operation_pact")
        self.assertIn("is_covert_operation_pact = yes", hostile)
        self.assertIn("NOT = { is_diplomatic_action_type = covert_counterintel_support_action }", hostile)

    def test_ai_wants_priority_one(self):
        ai = scripted_effect("covert_ai_manage_priorities")
        # The escalation branches sit behind the hostile check.
        self.assertLess(ai.index(HOSTILE), ai.index("has_war_with = scope:iw_ai_target"))
        self.assertLess(ai.index(HOSTILE), ai.index("type = rivalry"))

    def test_cultivate_assets_ai_counts_only_hostile_operations(self):
        score = blocks(action("cultivate_assets"), "propose_score")[0]
        self.assertIn(HOSTILE, score)

    def test_slots_and_upkeep_still_count_it(self):
        # It costs a slot and upkeep like any operation (spec § C).
        values = _text(ROOT / "common/script_values/covert_warfare_script_values.txt")
        active = _top_level_block(values, "covert_operations_active = {")
        self.assertIn("is_covert_operation_pact = yes", active)
        self.assertNotIn("covert_op_is_hostile", scripted_effect("covert_refresh_priority_cost"))


class ProtectorTest(unittest.TestCase):
    """One protector per ally, recorded on the ally as iw_cis_protector."""

    def test_create_sets_it(self):
        create = scripted_effect("covert_op_create")
        self.assertRegex(create, r"set_variable = \{ name = iw_cis_protector value = scope:iw_operator \}")

    def test_destroy_and_reap_clear_only_their_own(self):
        for name in ("covert_op_destroy", "covert_op_sync"):
            body = scripted_effect(name)
            self.assertRegex(body, r"var:iw_cis_protector \?= scope:\w+\s*\}\s*remove_variable = iw_cis_protector",
                             name)

    def test_every_country_drops_a_stale_mark(self):
        monthly = _top_level_block(_text(ON_ACTIONS), "covert_warfare_monthly_country = {")
        self.assertIn("has_variable = iw_cis_protector", monthly)
        self.assertIn(
            "has_diplomatic_pact = { who = ROOT type = covert_counterintel_support_action is_initiator = yes }",
            monthly,
        )
        self.assertIn("remove_variable = iw_cis_protector", monthly)


class RowTest(unittest.TestCase):
    def test_row_shows_no_detection_figure(self):
        row = _text(WIDGET)
        row = row[row.index("type widget_je_covert_operation_row"):]
        line = row[row.rindex("widget_je_covert_operation_detail = {", 0, row.index('text = "je_iw_op_row_detection"')):
                   row.index('text = "je_iw_op_row_detection"')]
        self.assertIn("Not( ScriptContainer.HasTag('iw_op_counterintel_support') )", line)
        self.assertRegex(
            row,
            r"visible = \"\[ScriptContainer\.HasTag\('iw_op_counterintel_support'\)\]\"\s*"
            r"text = \"je_iw_op_row_detection_none\"",
        )
        loc = _loc()
        self.assertNotIn("%", loc["je_iw_op_row_detection_none"])
        self.assertNotIn("JournalEntry", loc["je_iw_op_row_detection_none_tt"])


if __name__ == "__main__":
    unittest.main()
