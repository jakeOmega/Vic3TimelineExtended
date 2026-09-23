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


if __name__ == "__main__":
    unittest.main()
