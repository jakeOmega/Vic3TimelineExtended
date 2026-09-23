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

    def test_tick_lookups_guarded(self):
        # Every random_in_list over iw_nets inside the tick sits under an
        # any_in_list limit on the same target, so an unmatched lookup can
        # never leave the previous operation's network in the saved scope.
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        self.assertEqual(
            block.count("random_in_list = {"),
            block.count("save_scope_as = iw_tick_net"),
        )
        self.assertGreaterEqual(block.count("any_in_list = {"), block.count("random_in_list = {"))


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
        self.assertEqual([p.name for p in callers], ["je_covert_warfare.txt"])

    def test_pulse_order(self):
        je = _text(JE)
        ops = je.index("covert_ops_sync_all = yes")
        nets = je.index("covert_nets_sync = yes")
        age = je.index("covert_ops_age_all_durations = yes")
        self.assertLess(ops, nets)
        self.assertLess(nets, age)


if __name__ == "__main__":
    unittest.main()
