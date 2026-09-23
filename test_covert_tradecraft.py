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


if __name__ == "__main__":
    unittest.main()
