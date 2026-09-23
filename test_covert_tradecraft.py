"""Structural tests for covert warfare slice 5 (agency experience, "Tradecraft").

Tradecraft is one country variable, iw_tradecraft (0-100), written only by
covert_tradecraft_gain / covert_tradecraft_loss. These tests pin the spec's
constants, the tier table, that the score moves once a month and only from the
journal entry pulse, that a burn is charged by tier before the event cleans up
the type code, that the unlocks gate only what the spec says they gate, and
that the widget, loc and harness exist.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
EVENTS = ROOT / "events/covert_warfare_events.txt"
JE = ROOT / "common/journal_entries/je_covert_warfare.txt"
STATIC = ROOT / "common/static_modifiers/extra_modifiers.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/covert_warfare_custom_loc.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_covert_events.txt"
LOC_DIR = ROOT / "localization/english"


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace. Safe because nested closing braces are always
    tab-indented (format_paradox_tabs.py)."""
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}\n") + 3]


def _all_loc():
    return "".join(p.read_text(encoding="utf-8-sig") for p in LOC_DIR.rglob("*.yml"))


class ConstantTests(unittest.TestCase):
    def test_constants_exist(self):
        body = _text(VALUES)
        for name, value in (
            ("covert_tradecraft_max", "100"),
            ("covert_tradecraft_gain_per_op", "1"),
            ("covert_tradecraft_ops_counted", "4"),
            ("covert_tradecraft_dr_divisor", "50"),
            ("covert_tradecraft_dr_floor", "0.1"),
            ("covert_tradecraft_loss_mild", "3"),
            ("covert_tradecraft_loss_moderate", "6"),
            ("covert_tradecraft_loss_severe", "9"),
            ("covert_tradecraft_loss_war", "3"),
            ("covert_tradecraft_decay", "0.25"),
            ("covert_tradecraft_tier_1_floor", "20"),
            ("covert_tradecraft_tier_2_floor", "40"),
            ("covert_tradecraft_tier_3_floor", "60"),
            ("covert_tradecraft_tier_4_floor", "80"),
            ("covert_tradecraft_net_gain_per_tier", "0.15"),
        ):
            self.assertRegex(body, r"(?m)^%s = %s$" % (name, re.escape(value)))

    def test_losses_rise_with_tier(self):
        body = _text(VALUES)
        get = lambda n: float(re.search(r"(?m)^%s = ([\d.]+)$" % n, body).group(1))
        self.assertLess(get("covert_tradecraft_loss_mild"), get("covert_tradecraft_loss_moderate"))
        self.assertLess(get("covert_tradecraft_loss_moderate"), get("covert_tradecraft_loss_severe"))


class ScriptValueTests(unittest.TestCase):
    def test_gain_scale_mirrors_un_idiom(self):
        block = _top_level_block(_text(VALUES), "covert_tradecraft_gain_scale = {")
        self.assertIn("covert_tradecraft_dr_divisor", block)
        self.assertIn("min = covert_tradecraft_dr_floor", block)
        self.assertIn("max = 1", block)
        self.assertIn("has_variable = iw_tradecraft", block)

    def test_monthly_gain_reads_counted_ops(self):
        block = _top_level_block(_text(VALUES), "covert_tradecraft_monthly_gain_nominal = {")
        self.assertIn("var:iw_tradecraft_ops", block)
        self.assertIn("covert_tradecraft_gain_per_op", block)

    def test_tier_counts_all_four_floors(self):
        block = _top_level_block(_text(VALUES), "covert_tradecraft_tier = {")
        for n in range(1, 5):
            self.assertIn("covert_tradecraft_tier_%d = yes" % n, block)

    def test_bonus_mult_hops_owner(self):
        # Evaluated as a journal-entry modifier multiplier: JE scope.
        block = _top_level_block(_text(VALUES), "covert_tradecraft_bonus_mult = {")
        self.assertIn("owner = {", block)
        self.assertIn("covert_tradecraft_tier", block)

    def test_net_gain_mult_is_one_plus_tier_share(self):
        block = _top_level_block(_text(VALUES), "covert_tradecraft_net_gain_mult = {")
        self.assertIn("covert_tradecraft_tier", block)
        self.assertIn("covert_tradecraft_net_gain_per_tier", block)
        self.assertIn("add = 1", block)

    def test_burn_loss_value_branches_every_tier(self):
        block = _top_level_block(_text(VALUES), "covert_tradecraft_burn_loss_value = {")
        for tier in ("mild", "severe", "war"):
            self.assertIn("covert_code_tier_%s = { VAR = iw_burned_type_code }" % tier, block)
            self.assertIn("covert_tradecraft_loss_%s" % tier, block)
        # Unrecognised codes read as moderate, like the blowback values.
        self.assertRegex(block, r"else = \{\s*add = covert_tradecraft_loss_moderate")


class TriggerTests(unittest.TestCase):
    def test_tier_triggers_use_floors_and_guard(self):
        body = _text(TRIGGERS)
        for n in range(1, 5):
            block = _top_level_block(body, "covert_tradecraft_tier_%d = {" % n)
            self.assertIn("has_variable = iw_tradecraft", block)
            self.assertIn("var:iw_tradecraft >= covert_tradecraft_tier_%d_floor" % n, block)

    def test_unlock_triggers_map_to_spec_tiers(self):
        body = _text(TRIGGERS)
        for name, tier in (
            ("covert_tradecraft_unlocks_priority_3", 2),
            ("covert_tradecraft_unlocks_severe_ops", 3),
            ("covert_tradecraft_unlocks_extra_per_type", 4),
        ):
            block = _top_level_block(body, name + " = {")
            self.assertIn("covert_tradecraft_tier_%d = yes" % tier, block)


class WriterTests(unittest.TestCase):
    def test_writers_guard_missing_variable(self):
        body = _text(EFFECTS)
        for name in ("covert_tradecraft_gain = {", "covert_tradecraft_loss = {"):
            block = _top_level_block(body, name)
            self.assertIn("has_variable = iw_tradecraft", block)
            self.assertIn("covert_tradecraft_clamp = yes", block)
            self.assertIn("iw_tradecraft_last_reason", block)
            # Rule 1: never change_variable with a script-value operand.
            self.assertNotIn("change_variable", block)

    def test_gain_scaled_loss_unscaled(self):
        body = _text(EFFECTS)
        self.assertIn("covert_tradecraft_gain_scale", _top_level_block(body, "covert_tradecraft_gain = {"))
        self.assertNotIn("covert_tradecraft_gain_scale", _top_level_block(body, "covert_tradecraft_loss = {"))

    def test_clamp_bounds(self):
        block = _top_level_block(_text(EFFECTS), "covert_tradecraft_clamp = {")
        self.assertIn("clamp_variable = { name = iw_tradecraft min = 0 max = covert_tradecraft_max }", block)


class MonthlyTests(unittest.TestCase):
    def test_monthly_called_only_from_pulse(self):
        # covert_ops_sync_all / covert_refresh_funding_state run on every click;
        # the score must move once a month.
        effects = _text(EFFECTS)
        calls = re.findall(r"covert_tradecraft_monthly = yes", effects)
        self.assertEqual(calls, [], "covert_tradecraft_monthly must not be called from another effect")
        je = _text(JE)
        self.assertEqual(je.count("covert_tradecraft_monthly = yes"), 1)
        pulse = je[je.index("on_monthly_pulse"):]
        self.assertLess(pulse.index("covert_ops_age_all_durations = yes"), pulse.index("covert_tradecraft_monthly = yes"))
        self.assertLess(pulse.index("covert_tradecraft_monthly = yes"), pulse.index("covert_ops_roll_detection_all = yes"))

    def test_monthly_counts_established_ops_capped(self):
        block = _top_level_block(_text(EFFECTS), "covert_tradecraft_monthly = {")
        self.assertIn("covert_tradecraft_init = yes", block)
        self.assertIn("covert_op_is_established = yes", block)
        self.assertIn("max = covert_tradecraft_ops_counted", block)
        self.assertIn("covert_tradecraft_gain = { AMOUNT = covert_tradecraft_monthly_gain_nominal REASON = 1 }", block)
        self.assertIn("covert_operations_active < 1", block)
        self.assertIn("covert_tradecraft_loss = { AMOUNT = covert_tradecraft_decay REASON = 24 }", block)
        self.assertIn("covert_tradecraft_refresh_bonus = yes", block)

    def test_immediate_seeds(self):
        je = _text(JE)
        immediate = je[je.index("immediate = {"):je.index("complete = {")]
        self.assertIn("covert_tradecraft_init = yes", immediate)

    def test_bonus_modifier(self):
        block = _top_level_block(_text(STATIC), "iw_tradecraft_bonus = {")
        self.assertIn("country_intelligence_capacity_mult = 0.05", block)
        refresh = _top_level_block(_text(EFFECTS), "covert_tradecraft_refresh_bonus = {")
        self.assertIn("multiplier = covert_tradecraft_bonus_mult", refresh)
        self.assertIn("je:je_covert_warfare", refresh)
        loc = _all_loc()
        self.assertRegex(loc, r"(?m)^ iw_tradecraft_bonus:0 ")
        self.assertRegex(loc, r"(?m)^ iw_tradecraft_bonus_desc:0 ")


class BurnLossTests(unittest.TestCase):
    def test_burn_loss_branches_by_tier(self):
        block = _top_level_block(_text(EFFECTS), "covert_tradecraft_burn_loss = {")
        for tier, reason in (("mild", 20), ("severe", 22), ("war", 23)):
            self.assertIn("covert_code_tier_%s = { VAR = iw_burned_type_code }" % tier, block)
            self.assertIn(
                "covert_tradecraft_loss = { AMOUNT = covert_tradecraft_loss_%s REASON = %d }" % (tier, reason),
                block,
            )
        self.assertIn(
            "covert_tradecraft_loss = { AMOUNT = covert_tradecraft_loss_moderate REASON = 21 }", block
        )

    def test_burn_loss_before_cleanup(self):
        body = _text(EVENTS)
        event = _top_level_block(body, "covert_warfare.1 = {")
        after = event[event.index("\tafter = {"):]
        call = after.index("covert_tradecraft_burn_loss = yes")
        self.assertLess(after.index("covert_op_burn = { TYPE = destabilization"), call)
        self.assertLess(call, after.index("remove_variable = iw_burned_type_code"))
        # Inside the same guard as the burn: charged only when a burn happened.
        guard = after.index("exists = scope:detected_by_country")
        self.assertLess(guard, call)
        self.assertLess(call, after.index("trigger_event = { id = covert_warfare.2 }"))

    def test_burned_tooltip_names_loss(self):
        self.assertRegex(
            _all_loc(),
            r"(?m)^ covert_op_burned_tt:0 .*covert_tradecraft_burn_loss_value",
        )


class ConsumerTests(unittest.TestCase):
    def test_priority_gate_only_on_step_to_three(self):
        body = _text(TRIGGERS)
        up = _top_level_block(body, "covert_possible_priority_up = {")
        self.assertIn("text = iw_priority_3_needs_tradecraft_tt", up)
        self.assertIn("covert_tradecraft_unlocks_priority_3 = yes", up)
        # An operation below priority 2 steps freely.
        self.assertIn("NOT = { covert_op_priority_at_least = { N = 2 } }", up)
        down = _top_level_block(body, "covert_possible_priority_down = {")
        self.assertNotIn("tradecraft", down)
        # The AI goes through the same trigger.
        ai = _top_level_block(_text(EFFECTS), "covert_ai_manage_priorities = {")
        self.assertIn("covert_possible_priority_up = yes", ai)

    def test_per_type_cap_veteran(self):
        block = _top_level_block(_text(VALUES), "covert_ops_max_per_type = {")
        self.assertIn("covert_tradecraft_unlocks_extra_per_type = yes", block)
        self.assertIn("mainframe_computers", block)

    def test_net_multiplier_copied_before_gain(self):
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        stage = block.index("set_variable = { name = iw_tc_net_mult_staging value = covert_tradecraft_net_gain_mult }")
        tick = block.index("# ---- 3. Tick ----")
        copy = block.index("set_variable = { name = iw_net_tc_mult value = scope:iw_net_operator.var:iw_tc_net_mult_staging }")
        gain = block.index("covert_net_gain = { AMOUNT = covert_net_tick_gain }")
        self.assertLess(stage, tick)
        self.assertLess(tick, copy)
        self.assertLess(copy, gain)
        self.assertIn("remove_variable = iw_tc_net_mult_staging", block[gain:])

    def test_tick_gain_reads_multiplier(self):
        block = _top_level_block(_text(VALUES), "covert_net_tick_gain = {")
        self.assertIn("has_variable = iw_net_tc_mult", block)
        self.assertIn("multiply = var:iw_net_tc_mult", block)

    def test_gate_loc(self):
        loc = _all_loc()
        self.assertRegex(loc, r"(?m)^ iw_priority_3_needs_tradecraft_tt:0 .*covert_tradecraft_tier_2_floor")
        self.assertRegex(loc, r"(?m)^ je_iw_slots_detail_tooltip:0 .*covert_tradecraft_tier_4_floor")


class DisplayTests(unittest.TestCase):
    def test_custom_loc_tier_names_cover_every_band(self):
        block = _top_level_block(_text(CUSTOM_LOC), "covert_tradecraft_tier_name = {")
        for n in range(0, 5):
            self.assertIn("iw_tradecraft_tier_name_%d" % n, block)
        for n in range(1, 5):
            self.assertIn("covert_tradecraft_tier_%d = yes" % n, block)

    def test_custom_loc_reasons_cover_every_code(self):
        block = _top_level_block(_text(CUSTOM_LOC), "covert_tradecraft_last_reason = {")
        for code in (1, 20, 21, 22, 23, 24):
            self.assertIn("var:iw_tradecraft_last_reason = %d" % code, block)
            self.assertIn("iw_tradecraft_reason_%d" % code, block)

    def test_widget_row(self):
        body = _text(WIDGET)
        cc = body[body.index('name = "widget_je_covert_command_centre"'):body.index('name = "widget_je_covert_operations"')]
        self.assertIn('text = "je_iw_tradecraft_header"', cc)
        self.assertIn('text = "je_iw_tradecraft_line"', cc)
        self.assertIn('tooltip = "je_iw_tradecraft_tooltip"', cc)
        self.assertLess(cc.index("je_iw_funding_header"), cc.index("je_iw_tradecraft_header"))
        self.assertLess(cc.index("je_iw_tradecraft_header"), cc.index("je_iw_detection_header"))

    def test_loc_keys_exist(self):
        loc = _all_loc()
        keys = ["je_iw_tradecraft_header", "je_iw_tradecraft_line", "je_iw_tradecraft_tooltip"]
        keys += ["iw_tradecraft_tier_name_%d" % n for n in range(5)]
        keys += ["iw_tradecraft_reason_%d" % c for c in (0, 1, 20, 21, 22, 23, 24)]
        keys += ["te_debug_covert.3.t", "te_debug_covert.3.d", "te_debug_covert.3.f"]
        keys += ["te_debug_covert.3.%s" % o for o in "abc"]
        for key in keys:
            self.assertRegex(loc, r"(?m)^ %s:0 " % re.escape(key), key)

    def test_harness(self):
        effects = _text(DEBUG_EFFECTS)
        setter = _top_level_block(effects, "te_debug_covert_set_tradecraft = {")
        self.assertIn("covert_tradecraft_init = yes", setter)
        self.assertIn("covert_tradecraft_clamp = yes", setter)
        self.assertIn("covert_tradecraft_refresh_bonus = yes", setter)
        tick = _top_level_block(effects, "te_debug_covert_tick_tradecraft = {")
        self.assertIn("covert_tradecraft_monthly = yes", tick)
        event = _top_level_block(_text(DEBUG_EVENTS), "te_debug_covert.3 = {")
        self.assertIn("REVIEWED", event.splitlines()[0])
        self.assertIn("te_debug_covert_set_tradecraft = { VALUE = 45 }", event)
        self.assertIn("te_debug_covert_set_tradecraft = { VALUE = 85 }", event)
        self.assertIn("te_debug_covert_tick_tradecraft = yes", event)


if __name__ == "__main__":
    unittest.main()
