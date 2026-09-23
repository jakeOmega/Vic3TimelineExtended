"""Structural tests for covert warfare slice 3 (per-operation priority).

Priority is one container variable. These tests pin where it is written,
that every effect is scaled through constant script values (the engine
re-evaluates an add_modifier multiplier against ROOT, so a container-scope
value cannot be one), that upkeep and detection read it, and that the row
stepper fails closed.
"""

import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
SGUIS = ROOT / "common/scripted_guis/covert_warfare_sguis.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui"
JE = ROOT / "common/journal_entries/je_covert_warfare.txt"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_covert_events.txt"
LOC_DIR = ROOT / "localization/english"

MULT_VALUES = tuple(
    "covert_op_mult_p%d_pri%d" % (phase, pri) for phase in (2, 3) for pri in (1, 2, 3)
)


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace. Safe because nested closing braces are always
    tab-indented (format_paradox_tabs.py)."""
    block = body[body.index(header):]
    return block[: block.index("\n}\n") + 3]


def _all_loc():
    return "".join(p.read_text(encoding="utf-8-sig") for p in LOC_DIR.rglob("*.yml"))


class PriorityVariableTests(unittest.TestCase):
    def test_create_writes_priority_one(self):
        create = _top_level_block(_text(EFFECTS), "covert_op_create = {")
        self.assertIn("set_variable = { name = iw_priority value = 1 }", create)

    def test_sync_backfills_priority_before_refreshing_detection(self):
        # Detection reads the priority (Task 4), so an old-save container
        # must have one before covert_op_refresh_detection runs.
        sync = _top_level_block(_text(EFFECTS), "covert_op_sync = {")
        backfill = sync.index("NOT = { has_variable = iw_priority }")
        refresh = sync.rindex("covert_op_refresh_detection")
        self.assertLess(backfill, refresh)

    def test_priority_trigger_is_guarded(self):
        block = _top_level_block(_text(TRIGGERS), "covert_op_priority_at_least = {")
        self.assertIn("has_variable = iw_priority", block)
        self.assertIn("var:iw_priority >= $N$", block)


class EffectMultiplierTests(unittest.TestCase):
    def test_constants_exist(self):
        body = _text(VALUES)
        for name, value in (
            ("covert_op_priority_max", "3"),
            ("covert_op_priority_2_effect_mult", "1.35"),
            ("covert_op_priority_3_effect_mult", "1.6"),
            ("covert_op_priority_2_cost_mult", "1.6"),
            ("covert_op_priority_3_cost_mult", "2.4"),
            ("covert_op_priority_detect_add", "2"),
            ("covert_op_phase_full_mult", "2"),
        ):
            self.assertRegex(body, r"(?m)^%s = %s$" % (name, re.escape(value)))

    def test_six_multipliers_are_derived_from_the_constants(self):
        body = _text(VALUES)
        for name in MULT_VALUES:
            block = _top_level_block(body, "%s = {" % name)
            # Constant: no variable, scope or trigger read, so safe as a
            # multiplier the engine re-evaluates against ROOT.
            self.assertNotIn("var:", block, name)
            self.assertNotIn("limit", block, name)
        self.assertIn("covert_op_phase_full_mult", _top_level_block(body, "covert_op_mult_p3_pri1 = {"))
        self.assertIn("covert_op_priority_3_effect_mult", _top_level_block(body, "covert_op_mult_p3_pri3 = {"))
        self.assertIn("covert_op_priority_2_effect_mult", _top_level_block(body, "covert_op_mult_p2_pri2 = {"))

    def test_effect_mult_is_zero_before_establishing(self):
        block = _top_level_block(_text(VALUES), "covert_op_effect_mult = {")
        self.assertIn("value = 0", block)
        self.assertIn("covert_op_is_fully_operational = yes", block)
        self.assertIn("covert_op_is_established = yes", block)
        self.assertIn("covert_op_priority_at_least = { N = 3 }", block)

    def test_values_file_parses(self):
        parser = ParadoxFileParser()
        parser.parse_file(str(VALUES), apply_directives=False)
        for name in MULT_VALUES + ("covert_op_effect_mult",):
            self.assertIn(name, parser.data)


class ScaledApplicationTests(unittest.TestCase):
    def test_no_literal_phase_multiplier_is_left(self):
        body = _text(EFFECTS)
        self.assertNotRegex(
            body,
            r"multiplier = 2\b",
            "every phase multiplier must go through covert_op_add_scaled_modifier",
        )

    def test_helper_uses_all_six_constant_multipliers(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_add_scaled_modifier = {")
        for name in MULT_VALUES:
            self.assertIn("multiplier = %s" % name, block)
        self.assertIn("scope:iw_op = { covert_op_is_fully_operational = yes }", block)
        self.assertIn("scope:iw_op = { covert_op_is_established = yes }", block)

    def test_target_and_self_helpers_call_the_scaled_helper(self):
        body = _text(EFFECTS)
        for name in ("covert_op_apply_target_effect", "covert_op_apply_self_effect"):
            block = _top_level_block(body, "%s = {" % name)
            self.assertIn("covert_op_add_scaled_modifier = { MODIFIER = $MODIFIER$", block)

    def test_self_effect_picks_the_strongest_operation_not_the_best_phase(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_apply_self_effect = {")
        self.assertIn("ordered_in_list = {", block)
        self.assertIn("order_by = covert_op_effect_mult", block)
        self.assertIn("position = 0", block)
        self.assertIn("save_scope_as = iw_op", block)

    def test_every_bespoke_site_calls_the_helper(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_apply_all_phase_effects = {")
        for modifier in (
            "covert_infrastructure_sabotage",
            "covert_military_espionage",
            "covert_destabilization_separatist",
            "covert_destabilization_general",
        ):
            self.assertIn(
                "covert_op_add_scaled_modifier = { MODIFIER = %s MONTHS = 3 }" % modifier,
                block,
            )

    def test_ideological_pressure_scales_with_priority(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_apply_all_phase_effects = {")
        for pri in (1, 2, 3):
            self.assertIn("MULT = covert_op_mult_p2_pri%d" % pri, block)
        self.assertNotIn("MULT = 1 ", block)


class UpkeepTests(unittest.TestCase):
    COST_VALUES = (
        "covert_operation_cost_mult",
        "covert_operation_cost_at_next_up",
        "covert_operation_cost_at_next_down",
    )

    def test_cost_values_read_the_priority_weighted_units(self):
        body = _text(VALUES)
        for name in self.COST_VALUES:
            block = _top_level_block(body, "%s = {" % name)
            self.assertIn("add = covert_priority_cost_units", block, name)
            self.assertNotIn("covert_operations_active", block, name)

    def test_units_fall_back_to_the_pact_count_before_the_first_refresh(self):
        block = _top_level_block(_text(VALUES), "covert_priority_cost_units = {")
        self.assertIn("has_variable = iw_priority_cost_sum", block)
        self.assertIn("add = var:iw_priority_cost_sum", block)
        self.assertIn("add = covert_operations_active", block)

    def test_refresh_accumulates_with_set_variable_not_change_variable(self):
        # change_variable does not reliably resolve a script-value operand.
        block = _top_level_block(_text(EFFECTS), "covert_refresh_priority_cost = {")
        self.assertIn("covert_op_priority_3_cost_mult", block)
        self.assertIn("covert_op_priority_2_cost_mult", block)
        self.assertNotIn("change_variable", block)

    def test_upkeep_charges_the_higher_of_current_and_applied_priority(self):
        # Lowering priority after the pulse must not keep a stronger effect
        # running on a cheaper budget.
        body = _text(EFFECTS)
        refresh = _top_level_block(body, "covert_refresh_priority_cost = {")
        self.assertIn("covert_op_charged_priority_at_least", refresh)
        self.assertNotIn("covert_op_priority_at_least = {", refresh)
        apply_all = _top_level_block(body, "covert_ops_apply_all_phase_effects = {")
        self.assertIn("name = iw_priority_applied value = var:iw_priority", apply_all)
        self.assertIn("covert_refresh_priority_cost = yes", apply_all)
        self.assertLess(
            apply_all.index("iw_priority_applied"),
            apply_all.index("covert_op_apply_target_effect"),
            "the snapshot must precede the effects",
        )
        self.assertGreater(
            apply_all.rindex("covert_refresh_priority_cost = yes"),
            apply_all.rindex("covert_op_add_scaled_modifier"),
            "the upkeep refresh must follow the effects",
        )
        trigger = _top_level_block(_text(TRIGGERS), "covert_op_charged_priority_at_least = {")
        self.assertIn("has_variable = iw_priority_applied", trigger)

    def test_every_path_that_adds_or_ends_an_operation_refreshes_the_sum(self):
        body = _text(EFFECTS)
        for name in ("covert_op_create", "covert_op_destroy", "covert_ops_sync_all"):
            block = _top_level_block(body, "%s = {" % name)
            self.assertIn("covert_refresh_priority_cost = yes", block, name)


class DetectionTests(unittest.TestCase):
    def test_refresh_stages_the_priority_through_prev(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_refresh_detection = {")
        stage = block.index("name = iw_priority_staging value = PREV.var:iw_priority")
        chance = block.index("value = covert_operation_detection_chance")
        self.assertLess(stage, chance, "stage the priority before the chance is computed")
        self.assertNotIn("scope:iw_op.var:", block)
        self.assertIn("remove_variable = iw_priority_staging", block)

    def test_penalty_is_guarded_and_uses_the_constant(self):
        block = _top_level_block(_text(VALUES), "covert_op_priority_detect_penalty = {")
        self.assertIn("has_variable = iw_priority_staging", block)
        self.assertIn("multiply = covert_op_priority_detect_add", block)

    def test_penalty_is_added_before_covert_efficiency(self):
        block = _top_level_block(_text(VALUES), "covert_operation_detection_chance = {")
        add = block.index("add = covert_op_priority_detect_penalty")
        efficiency = block.index("modifier:country_covert_operation_efficiency_mult")
        self.assertLess(add, efficiency)


class StepperTests(unittest.TestCase):
    def test_identification_fails_closed(self):
        block = _top_level_block(_text(TRIGGERS), "covert_priority_op_is_ours = {")
        self.assertIn("exists = scope:iw_op", block)
        self.assertIn("is_target_in_variable_list = { name = iw_ops target = scope:iw_op }", block)
        self.assertIn("has_tag = iw_op", block)
        for name in ("covert_possible_priority_up", "covert_possible_priority_down"):
            gate = _top_level_block(_text(TRIGGERS), "%s = {" % name)
            self.assertIn("covert_priority_op_is_ours = yes", gate, name)
        self.assertIn(
            "covert_op_priority_max",
            _top_level_block(_text(TRIGGERS), "covert_possible_priority_up = {"),
        )

    def test_both_handlers_delegate_and_are_closed_to_the_ai(self):
        body = _text(SGUIS)
        for direction in ("up", "down"):
            block = _top_level_block(body, "covert_priority_%s_sgui = {" % direction)
            self.assertIn("saved_scopes = { iw_op }", block)
            self.assertIn("covert_possible_priority_%s = yes" % direction, block)
            self.assertIn("covert_effect_priority_%s = yes" % direction, block)
            self.assertRegex(block, r"ai_is_valid = \{\s*always = no\s*\}")

    def test_step_refreshes_cost_but_leaves_effects_to_the_pulse(self):
        block = _top_level_block(_text(EFFECTS), "covert_apply_priority_change = {")
        self.assertIn("covert_refresh_priority_cost = yes", block)
        self.assertIn("covert_refresh_funding_state = yes", block)
        self.assertNotIn("covert_ops_apply_all_phase_effects", block)

    def test_step_clamps_to_the_bounds(self):
        body = _text(EFFECTS)
        for direction in ("up", "down"):
            block = _top_level_block(body, "covert_effect_priority_%s = {" % direction)
            self.assertIn("clamp_variable = { name = iw_priority min = 1 max = covert_op_priority_max }", block)
            self.assertIn("covert_apply_priority_change = yes", block)

    def test_the_row_passes_its_container_in_a_single_addscope(self):
        gui = _text(WIDGET)
        call = "AddScope( 'iw_op', ScriptContainer.MakeScope )"
        self.assertEqual(gui.count(call), 4, "enabled + onclick on each of two buttons")
        self.assertIn("GetScriptedGui('covert_priority_up_sgui')", gui)
        self.assertIn("GetScriptedGui('covert_priority_down_sgui')", gui)

    def test_the_row_hides_priority_until_every_container_has_one(self):
        gui = _text(WIDGET)
        self.assertIn("covert_ops_priority_ready_sgui", gui)
        for pri in (1, 2, 3):
            self.assertIn("je_iw_op_row_priority_%d" % pri, gui)
        gate = _top_level_block(_text(SGUIS), "covert_ops_priority_ready_sgui = {")
        self.assertIn("NOT = { has_variable = iw_priority }", gate)

    def test_loc_keys_exist(self):
        loc = _all_loc()
        for key in (
            "iw_priority_op_known_tt", "iw_priority_op_ours_tt",
            "iw_priority_not_max_tt", "iw_priority_not_min_tt",
            "iw_priority_to_1_tt", "iw_priority_to_2_tt", "iw_priority_to_3_tt",
            "je_iw_priority_stepper_label",
            "je_iw_priority_step_up_tooltip", "je_iw_priority_step_down_tooltip",
            "je_iw_op_row_priority_1", "je_iw_op_row_priority_2", "je_iw_op_row_priority_3",
        ):
            self.assertIn(" %s:" % key, loc, key)


class AITests(unittest.TestCase):
    def test_ai_steps_through_the_shared_gates(self):
        block = _top_level_block(_text(EFFECTS), "covert_ai_manage_priorities = {")
        self.assertIn("covert_possible_priority_up = yes", block)
        self.assertIn("covert_possible_priority_down = yes", block)
        self.assertIn("covert_refresh_priority_cost = yes", block)
        self.assertIn("rank_value:great_power", block)
        self.assertIn("type = rivalry", block)
        self.assertIn("in_default = yes", block)
        self.assertIn("declared_bankruptcy", block)

    def test_pulse_runs_it_for_the_ai_before_the_sync(self):
        body = _text(JE)
        pulse = body[body.index("on_monthly_pulse = {"):]
        call = pulse.index("covert_ai_manage_priorities = yes")
        sync = pulse.index("covert_ops_sync_all = yes")
        self.assertLess(call, sync, "the sync must see the new priorities")
        guard = pulse.rfind("is_player = no", 0, call)
        self.assertNotEqual(guard, -1)


class HarnessTests(unittest.TestCase):
    def test_the_harness_changes_priority_through_the_shipping_effect(self):
        # Each step runs covert_ops_sync_all, whose detection refresh re-saves
        # scope:iw_op per container, so the pick is held under its own name
        # and re-saved before every step.
        block = _top_level_block(_text(DEBUG_EFFECTS), "te_debug_covert_max_priority = {")
        self.assertIn("save_scope_as = iw_debug_op", block)
        self.assertEqual(block.count("scope:iw_debug_op = { save_scope_as = iw_op }"), 2)
        self.assertEqual(block.count("covert_effect_priority_up = yes"), 2)

    def test_the_operations_console_offers_it(self):
        block = _top_level_block(_text(DEBUG_EVENTS), "te_debug_covert.2 = {")
        self.assertIn("te_debug_covert_max_priority = yes", block)
        self.assertIn(" te_debug_covert.2.h:", _all_loc())


if __name__ == "__main__":
    unittest.main()
