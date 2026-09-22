"""Structural tests for covert warfare slice 2 (graduated exposure).

The tier table is the single source of truth for how hostile each operation
type is when it is caught. These tests pin that table, pin that every consumer
reads it rather than re-listing codes, and pin the shape of the blowback the
detection event applies.
"""

import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
EVENTS = ROOT / "events/covert_warfare_events.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/covert_warfare_custom_loc.txt"
MESSAGES = ROOT / "common/messages/extra_messages.txt"
ACTIONS = ROOT / "common/diplomatic_actions/covert_operations.txt"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"

# Slice 1's codes, repeated here so this file stands alone.
CODES = {
    "election_interference": 0,
    "financial_subversion": 1,
    "infrastructure_sabotage": 2,
    "comms_disruption": 3,
    "industrial_espionage": 4,
    "military_espionage": 5,
    "influence_campaign": 6,
    "ideological_subversion": 7,
    "destabilization": 8,
}

TIER_CODES = {
    "mild": {4, 5},
    "moderate": {0, 1, 6},
    "severe": {7, 8},
    "war": {2, 3},
}

# Values slice 2 retires. None of them may survive anywhere in the mod.
RETIRED_VALUES = (
    "covert_detection_chance_display",
    "covert_detection_target_ic_display",
    "covert_ops_detected_infamy",
)

MOD_DIRS = ("common", "events", "gui", "localization")
MOD_SUFFIXES = {".txt", ".gui", ".yml"}


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """The text of one top-level `header = { ... }` entry, header through the
    first unindented closing brace. Safe because nested closing braces are
    always tab-indented (format_paradox_tabs.py).
    """
    block = body[body.index(header):]
    return block[: block.index("\n}\n") + 3]


def _tier_block(body, tier):
    return _top_level_block(body, "covert_code_tier_%s = {" % tier)


class TierTableTests(unittest.TestCase):
    def test_tier_triggers_partition_every_operation_code(self):
        # Slice 6 adds three operation types. Each new code must land in
        # exactly one tier, and no code may be forgotten.
        body = _text(TRIGGERS)
        seen = {}
        for tier, expected in TIER_CODES.items():
            codes = {int(m) for m in re.findall(r"var:\$VAR\$ = (\d+)", _tier_block(body, tier))}
            self.assertEqual(codes, expected, "tier %s holds the wrong codes" % tier)
            for code in codes:
                self.assertNotIn(code, seen, "code %d is in two tiers" % code)
                seen[code] = tier
        self.assertEqual(
            set(seen),
            set(CODES.values()),
            "every operation code must belong to exactly one exposure tier",
        )

    def test_tier_triggers_guard_the_variable(self):
        # Reading a variable that does not exist logs an engine error, and
        # these run from custom loc that may render before the code is stamped.
        body = _text(TRIGGERS)
        for tier in TIER_CODES:
            self.assertIn(
                "has_variable = $VAR$",
                _tier_block(body, tier),
                "covert_code_tier_%s must guard $VAR$" % tier,
            )

    def test_triggers_file_parses(self):
        parser = ParadoxFileParser()
        parser.parse_file(str(TRIGGERS), apply_directives=False)
        for tier in TIER_CODES:
            self.assertIn("covert_code_tier_%s" % tier, parser.data)


class BlowbackValueTests(unittest.TestCase):
    def test_blowback_values_read_the_tier_table(self):
        body = _text(VALUES)
        for name in ("covert_exposure_infamy_base", "covert_exposure_relations_base"):
            block = _top_level_block(body, "%s = {" % name)
            self.assertIn("covert_code_tier_", block, "%s must branch on the tier table" % name)
            self.assertIn("VAR = iw_burned_type_code", block)

    def test_phase_multiplier_reads_the_burned_phase(self):
        block = _top_level_block(_text(VALUES), "covert_exposure_phase_mult = {")
        self.assertIn("has_variable = iw_burned_phase", block)
        self.assertIn("var:iw_burned_phase", block)

    def test_option_values_exist_and_split_the_blowback(self):
        body = _text(VALUES)
        ack_infamy = _top_level_block(body, "covert_exposure_infamy_acknowledge = {")
        deny_infamy = _top_level_block(body, "covert_exposure_infamy_deny = {")
        ack_rel = _top_level_block(body, "covert_exposure_relations_acknowledge = {")
        deny_rel = _top_level_block(body, "covert_exposure_relations_deny = {")
        # Acknowledge pays the full infamy; Deny halves it.
        self.assertIn("covert_exposure_phase_mult", ack_infamy)
        self.assertIn("covert_exposure_deny_infamy_mult", deny_infamy)
        # Deny takes the full relations hit; Acknowledge halves it.
        self.assertIn("covert_exposure_phase_mult", deny_rel)
        self.assertIn("covert_exposure_acknowledge_relations_mult", ack_rel)

    def test_infamy_is_capped(self):
        block = _top_level_block(_text(VALUES), "covert_exposure_infamy_acknowledge = {")
        self.assertIn("max = covert_exposure_infamy_max", block)

    def test_retired_values_have_no_references_left(self):
        for name in RETIRED_VALUES:
            for directory in MOD_DIRS:
                for path in sorted((ROOT / directory).rglob("*")):
                    if not path.is_file() or path.suffix not in MOD_SUFFIXES:
                        continue
                    self.assertNotIn(
                        name,
                        path.read_text(encoding="utf-8-sig", errors="ignore"),
                        "%s still appears in %s" % (name, path),
                    )


if __name__ == "__main__":
    unittest.main()
