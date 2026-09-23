"""Structural tests for covert warfare slice 4 (per-target networks).

A network is one script container per (operator, target), listed in the
operator's iw_nets. These tests pin the constants, that the monthly tick runs
once a month and only from the journal entry pulse, that every lookup of a
network from inside a loop is guarded (an unmatched random_in_list would leave
the previous iteration's scope behind), that old-save operations keep their
phase, and that the widget and loc exist.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui"
JE = ROOT / "common/journal_entries/je_covert_warfare.txt"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_covert_events.txt"
LOC_DIR = ROOT / "localization/english"


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace. Safe because nested closing braces are always
    tab-indented (format_paradox_tabs.py)."""
    # Anchored on a preceding newline so the header only matches a top-level
    # definition, never a mention inside a comment or an indented call.
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}\n") + 3]


def _all_loc():
    return "".join(p.read_text(encoding="utf-8-sig") for p in LOC_DIR.rglob("*.yml"))


class ConstantTests(unittest.TestCase):
    def test_constants_exist(self):
        body = _text(VALUES)
        for name, value in (
            ("covert_net_max", "100"),
            ("covert_net_dr_divisor", "50"),
            ("covert_net_dr_floor", "0.1"),
            ("covert_net_gain_base", "2"),
            ("covert_net_extra_op_factor", "0.5"),
            ("covert_net_decay_base", "1.5"),
            ("covert_net_maintain_funding_level", "3"),
            ("covert_net_maintain_decay_mult", "0.5"),
            ("covert_net_burn_loss", "25"),
            ("covert_net_detect_factor", "0.05"),
            ("covert_net_head_start_per_point", "0.05"),
            ("covert_net_head_start_max", "5"),
        ):
            self.assertRegex(body, r"(?m)^%s = %s$" % (name, re.escape(value)))

    def test_head_start_never_skips_preparatory(self):
        # Phase 2 starts at duration 6 (covert_op_is_established); a head start
        # of 6 or more would start an operation already establishing.
        body = _text(VALUES)
        cap = float(re.search(r"(?m)^covert_net_head_start_max = ([\d.]+)$", body).group(1))
        self.assertLess(cap, 6)


class ScriptValueTests(unittest.TestCase):
    def test_gain_scale_mirrors_un_idiom(self):
        block = _top_level_block(_text(VALUES), "covert_net_gain_scale = {")
        self.assertIn("covert_net_dr_divisor", block)
        self.assertIn("min = covert_net_dr_floor", block)
        self.assertIn("max = 1", block)

    def test_tick_gain_caps_at_three_ops(self):
        block = _top_level_block(_text(VALUES), "covert_net_tick_gain = {")
        self.assertIn("var:iw_net_ops", block)
        self.assertIn("max = 3", block)
        self.assertIn("covert_net_extra_op_factor", block)

    def test_head_start_rounded_and_capped(self):
        block = _top_level_block(_text(VALUES), "covert_net_head_start_value = {")
        self.assertIn("round = yes", block)
        self.assertIn("max = covert_net_head_start_max", block)

    def test_effective_duration_guards_missing_head_start(self):
        block = _top_level_block(_text(VALUES), "covert_op_effective_duration = {")
        self.assertIn("value = var:iw_duration", block)
        self.assertIn("has_variable = iw_net_head_start", block)

    def test_detection_subtracts_network_before_target_penalty(self):
        block = _top_level_block(_text(VALUES), "covert_operation_detection_chance = {")
        net = block.index("subtract = covert_net_detect_reduction")
        funding5 = block.index("covert_ops_detection_funding_5_reduction")
        target = block.index("add = target_counterintelligence_penalty")
        self.assertLess(funding5, net)
        self.assertLess(net, target)
        self.assertIn("min = covert_ops_detection_floor", block)


class NetworkEffectTests(unittest.TestCase):
    def test_create_is_tagged_parented_listed(self):
        block = _top_level_block(_text(EFFECTS), "covert_net_create = {")
        self.assertIn("tags = { iw_net }", block)
        self.assertIn("parent = scope:iw_net_operator", block)
        self.assertIn("add_to_variable_list = { name = iw_nets", block)
        self.assertIn("exists = scope:iw_new_net", block)
        # No duplicate network per target.
        self.assertIn("any_in_list", block)

    def test_gain_scaled_loss_not(self):
        body = _text(EFFECTS)
        gain = _top_level_block(body, "covert_net_gain = {")
        loss = _top_level_block(body, "covert_net_loss = {")
        self.assertIn("covert_net_gain_scale", gain)
        self.assertNotIn("covert_net_gain_scale", loss)
        self.assertIn("covert_net_clamp = yes", gain)
        self.assertIn("covert_net_clamp = yes", loss)

    def test_tick_counts_by_accumulation(self):
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        self.assertIn("set_variable = { name = iw_net_ops value = 0 }", block)
        self.assertIn("change_variable = { name = iw_net_ops add = 1 }", block)
        self.assertNotRegex(block, r"count\s*>=")

    def test_tick_halves_decay_on_funding(self):
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        self.assertIn("covert_net_maintain_funding_level", block)
        self.assertIn("covert_net_loss = { AMOUNT = covert_net_decay_maintained }", block)
        self.assertIn("covert_net_loss = { AMOUNT = covert_net_decay_base }", block)
        self.assertIn("covert_net_gain = { AMOUNT = covert_net_tick_gain }", block)

    def test_reap_removes_before_destroy(self):
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        reap = block[block.index("add_to_temporary_list = iw_reaped_nets"):]
        self.assertLess(
            reap.index("remove_list_variable = { name = iw_nets"),
            reap.index("destroy_container = yes"),
        )

    def test_reap_checks_dead_target(self):
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        self.assertIn("is_country_alive = yes", block)

    def test_tick_counts_inside_the_lookup(self):
        # The count is added inside random_in_list, so an operation whose
        # target has no network adds to nothing rather than to the previous one.
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        pick = block[block.index("random_in_list = {"):]
        self.assertLess(
            pick.index("limit = { var:iw_target ?= scope:iw_net_count_tgt }"),
            pick.index("change_variable = { name = iw_net_ops add = 1 }"),
        )
        self.assertNotIn("save_scope_as", pick[: pick.index("change_variable")])


class PulseOrderTests(unittest.TestCase):
    def test_nets_sync_only_called_from_monthly_pulse(self):
        # covert_ops_sync_all also runs on every funding / priority click;
        # a tick in there would grow networks per click.
        effects = _text(EFFECTS)
        sync_all = _top_level_block(effects, "covert_ops_sync_all = {")
        refresh = _top_level_block(effects, "covert_refresh_funding_state = {")
        self.assertNotIn("covert_nets_sync", sync_all)
        self.assertNotIn("covert_nets_sync", refresh)
        callers = [
            p for p in ROOT.glob("common/**/*.txt")
            if "covert_nets_sync = yes" in p.read_text(encoding="utf-8-sig")
        ]
        self.assertEqual(
            sorted(p.name for p in callers),
            ["je_covert_warfare.txt", "te_debug_covert_effects.txt"],
        )

    def test_pulse_order(self):
        je = _text(JE)
        ops = je.index("covert_ops_sync_all = yes")
        nets = je.index("covert_nets_sync = yes")
        age = je.index("covert_ops_age_all_durations = yes")
        self.assertLess(ops, nets)
        self.assertLess(nets, age)


class ConsumerTests(unittest.TestCase):
    def test_head_start_set_before_phase_refresh(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_create = {")
        self.assertLess(
            block.index("iw_net_head_start"),
            block.index("covert_op_refresh_phase = yes"),
        )
        self.assertIn("PREV.var:iw_net_head_start_offer", block)

    def test_head_start_defaults_to_zero_before_lookup(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_create = {")
        zero = block.index("set_variable = { name = iw_net_head_start value = 0 }")
        pick = block.index("random_in_list = {")
        self.assertLess(zero, pick)
        self.assertIn("limit = { var:iw_target ?= $TARGET$ }", block[pick:])

    def test_op_create_ensures_network_after_lookup(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_create = {")
        self.assertLess(
            block.index("PREV.var:iw_net_head_start_offer"),
            block.index("covert_net_create"),
        )

    def test_detection_lookup_zeroed_first(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_refresh_detection = {")
        zero = block.index("set_variable = { name = iw_net_strength_staging value = 0 }")
        pick = block.index("random_in_list = {")
        read = block.index("PREV.var:iw_net_strength")
        chance = block.index("covert_operation_detection_chance")
        self.assertLess(zero, pick)
        self.assertLess(pick, read)
        self.assertLess(read, chance)
        self.assertIn("remove_variable = iw_net_strength_staging", block)

    def test_sync_backfills_head_start_before_detection(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_sync = {")
        backfill = block.index("NOT = { has_variable = iw_net_head_start }")
        refresh = block.rindex("covert_op_refresh_detection")
        self.assertLess(backfill, refresh)

    def test_phase_triggers_read_effective_duration(self):
        body = _text(TRIGGERS)
        est = _top_level_block(body, "covert_op_is_established = {")
        full = _top_level_block(body, "covert_op_is_fully_operational = {")
        self.assertIn("covert_op_effective_duration >= 6", est)
        self.assertIn("covert_op_effective_duration >= 12", full)
        self.assertNotIn("var:iw_duration", est + full)

    def test_refresh_phase_uses_effective_duration(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_refresh_phase = {")
        self.assertEqual(block.count("subtract = covert_op_effective_duration"), 2)
        self.assertNotIn("subtract = var:iw_duration", block)

    def test_burn_costs_the_network(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_burn = {")
        pick = block[block.index("random_in_list = {"):]
        self.assertLess(
            pick.index("limit = { var:iw_target ?= $TARGET$ }"),
            pick.index("covert_net_loss = { AMOUNT = covert_net_burn_loss }"),
        )


NET_LOC_KEYS = (
    "je_iw_net_header",
    "je_iw_net_header_tooltip",
    "je_iw_net_row_title",
    "je_iw_net_row_strength",
    "je_iw_net_row_trend_growing",
    "je_iw_net_row_trend_decaying",
    "je_iw_net_row_trend_holding",
    "je_iw_net_row_benefit",
)


class WidgetTests(unittest.TestCase):
    def test_je_mounts_network_widget_on_container_3(self):
        je = _text(JE)
        self.assertRegex(
            je,
            r'name = "widget_je_covert_networks"\s*\n\s*container = "custom_widget_container_3"',
        )

    def test_network_widget_gated(self):
        gui = _text(WIDGET)
        root = gui[gui.index('name = "widget_je_covert_networks"'):]
        self.assertIn('visible = "[JournalEntry.IsActive]"', root[:400])
        self.assertIn("GetList('iw_nets')", root)
        self.assertIn("IsDataModelEmpty", root)

    def test_trend_lines_cover_all_three_codes(self):
        gui = _text(WIDGET)
        for code in ("0", "1", "2"):
            self.assertIn(
                "EqualTo_CFixedPoint(ScriptContainer.GetVariableValue('iw_net_trend'), '(CFixedPoint)%s')" % code,
                gui,
            )

    def test_loc_keys_exist(self):
        loc = _all_loc()
        for key in NET_LOC_KEYS:
            self.assertRegex(loc, r"(?m)^ %s:0 " % re.escape(key))


class HarnessTests(unittest.TestCase):
    def test_harness_effects(self):
        body = _text(DEBUG_EFFECTS)
        setter = _top_level_block(body, "te_debug_covert_set_net_strength = {")
        self.assertIn("covert_nets_sync = yes", setter)  # ensures nets exist first
        self.assertIn("covert_ops_sync_all = yes", setter)  # re-stages detection
        tick = _top_level_block(body, "te_debug_covert_tick_nets = {")
        self.assertIn("covert_nets_sync = yes", tick)

    def test_harness_options_have_loc(self):
        events = _text(DEBUG_EVENTS)
        loc = _all_loc()
        for opt in ("te_debug_covert.2.i", "te_debug_covert.2.j"):
            self.assertIn("name = %s" % opt, events)
            self.assertRegex(loc, r"(?m)^ %s:0 " % re.escape(opt))


class ReviewFixTests(unittest.TestCase):
    def test_network_lookups_work_inside_the_iterator(self):
        # No saved scope for a looked-up network: the work happens inside
        # random_in_list itself. A saved scope can be unset in the render pass
        # the engine runs for scripted-GUI and event-option tooltips (rule 6),
        # and inside a loop an unmatched pick would leave the previous one.
        body = _text(EFFECTS)
        for name in ("iw_create_net", "iw_det_net", "iw_tick_net", "iw_burn_net"):
            self.assertNotIn("save_scope_as = %s" % name, body)

    def test_offer_restated_on_every_strength_write(self):
        # A burn must shrink the head start a same-day relaunch gets.
        block = _top_level_block(_text(EFFECTS), "covert_net_clamp = {")
        self.assertIn(
            "set_variable = { name = iw_net_head_start_offer value = covert_net_head_start_value }",
            block,
        )


if __name__ == "__main__":
    unittest.main()
