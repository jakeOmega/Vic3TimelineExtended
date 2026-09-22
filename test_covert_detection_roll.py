"""Structural regression test for the covert per-operation detection roll
(spec: docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md,
slice 1).

The engine cannot be run in CI, so these tests pin the *shape* of the script
the slice changed: the pulse rolls per operation through one named effect, the
old country-level roll and its target_max_ic restore block are gone, the
detection event is driven by scope:iw_burned_op, and every site that maps an
operation type to its code (covert_op_create, covert_op_sync, the nine
covert_op_start calls, covert_warfare.1's `after` branches, and
covert_burned_type_name) agrees with the pinned CODES mapping. A refactor that
silently re-introduces the single roll, or drops or renumbers a CODE at any of
those sites, fails here rather than in a play test.

Run: python3 test_covert_detection_roll.py
"""

import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
JE = ROOT / "common/journal_entries/je_covert_warfare.txt"
EVENTS = ROOT / "events/covert_warfare_events.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/covert_warfare_custom_loc.txt"
DIPLOMATIC_ACTIONS = ROOT / "common/diplomatic_actions/covert_operations.txt"
TE_DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"
TE_DEBUG_EVENTS = ROOT / "events/te_debug_covert_events.txt"

# Operation type code mapping, per covert_last_exposed_type_name /
# covert_burned_type_name. Pinned here once so every site below is checked
# against the same numbers rather than hand-copied per test.
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


def _parse(path):
    p = ParadoxFileParser()
    p.parse_file(str(path), apply_directives=False)
    return p.data


def _val(node):
    """The parser stores every field as an ('=', value) tuple; unwrap one."""
    return node[1] if isinstance(node, tuple) else node


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """The text of one top-level `header = { ... }` entry, header through the
    first unindented closing brace. Safe because nested closing braces are
    always tab-indented (format_paradox_tabs.py), so `\\n}\\n` only matches
    the entry's own close, never one of its children's.
    """
    block = body[body.index(header):]
    return block[: block.index("\n}\n") + 3]


class RollEffectTests(unittest.TestCase):
    def test_roll_effect_is_defined_and_rolls_per_container(self):
        data = _parse(EFFECTS)
        self.assertIn("covert_ops_roll_detection_all", data)
        block = _top_level_block(_text(EFFECTS), "covert_ops_roll_detection_all = {")
        self.assertIn("random = {", block)
        self.assertIn("chance = covert_op_roll_chance", block)
        self.assertIn("add_to_temporary_list = iw_detected_ops", block)
        self.assertIn("random_in_list = {", block)
        self.assertIn("save_scope_as = iw_burned_op", block)
        self.assertIn("exists = scope:iw_burned_op", block)
        self.assertIn("trigger_event = { id = covert_warfare.1 }", block)

    def test_roll_chance_value_reads_the_container(self):
        data = _parse(VALUES)
        self.assertIn("covert_op_roll_chance", data)
        self.assertIn("covert_operation_detection_chance", data)
        roll = _val(data["covert_op_roll_chance"])
        self.assertEqual(_val(roll["value"]), "var:iw_detect")
        self.assertNotIn(
            "multiply",
            roll,
            "covert_op_roll_chance must not scale again: "
            "covert_ops_detection_multi_op_scale now lives inside "
            "covert_operation_detection_chance so the widget and the roll agree",
        )
        chance_block = _top_level_block(
            _text(VALUES), "covert_operation_detection_chance = {"
        )
        self.assertIn("multiply = covert_ops_detection_multi_op_scale", chance_block)

    def test_create_stamps_the_type_code(self):
        create = _top_level_block(_text(EFFECTS), "covert_op_create = {")
        self.assertIn("name = iw_type_code value = $CODE$", create)

    def test_every_sync_row_passes_the_pinned_code(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_sync_all = {")
        for op_type, code in CODES.items():
            m = re.search(
                r"covert_op_sync = \{[^}]*TYPE = %s [^}]*CODE = (\d+)"
                % re.escape(op_type),
                block,
            )
            self.assertIsNotNone(m, f"no CODE on the {op_type} sync row")
            self.assertEqual(
                int(m.group(1)), code, f"{op_type} sync row has the wrong CODE"
            )
        # The sync effect itself must still stamp the container (old-save backfill).
        sync = _top_level_block(_text(EFFECTS), "covert_op_sync = {")
        self.assertIn("name = iw_type_code value = $CODE$", sync)


class PulseTests(unittest.TestCase):
    def test_pulse_calls_the_roll_and_drops_the_country_roll(self):
        body = _text(JE)
        pulse = body[body.index("on_monthly_pulse = {"):]
        self.assertIn("covert_ops_roll_detection_all = yes", pulse)
        self.assertNotIn("covert_operation_detection_chance", pulse)
        self.assertNotIn("name = target_max_ic value = 0", pulse)
        self.assertNotIn("random_list", pulse)
        self.assertLess(
            pulse.index("covert_ops_apply_all_phase_effects = yes"),
            pulse.index("covert_ops_roll_detection_all = yes"),
            "the roll must run after phase effects, at the end of the pulse",
        )


class DetectionEventTests(unittest.TestCase):
    def test_event_is_driven_by_the_burned_op_scope(self):
        body = _text(EVENTS)
        ev = body[body.index("covert_warfare.1 = {"): body.index("covert_warfare.2 = {")]
        trigger = ev[ev.index("trigger = {"): ev.index("immediate = {")]
        self.assertIn("exists = scope:iw_burned_op", trigger)
        self.assertNotIn("random_scope_diplomatic_pact", ev)
        self.assertNotIn("scope:burned_pact", ev)
        immediate = ev[ev.index("immediate = {"): ev.index("option = {")]
        self.assertIn("save_scope_as = detected_by_country", immediate)
        self.assertIn("name = iw_burned_type_code", immediate)
        after = ev[ev.index("after = {"):]
        for code in range(9):
            self.assertIn(f"var:iw_burned_type_code = {code}", after)
        self.assertNotIn("scope:iw_burned_op", after)

    def test_after_branches_pair_each_code_with_its_type(self):
        body = _text(EVENTS)
        ev = body[body.index("covert_warfare.1 = {"): body.index("covert_warfare.2 = {")]
        after = ev[ev.index("after = {"):]
        for op_type, code in CODES.items():
            pattern = re.compile(
                r"limit = \{ var:iw_burned_type_code = %d \}\s*"
                r"covert_op_burn = \{[^}]*TYPE = %s [^}]*CODE = %d[^}]*\}"
                % (code, re.escape(op_type), code)
            )
            self.assertIsNotNone(
                pattern.search(after),
                f"after branch for code {code} does not pair "
                f"TYPE = {op_type} with CODE = {code}",
            )

    def test_burned_type_code_is_removed_outside_the_detected_by_guard(self):
        # F8: the country must lose iw_burned_type_code even when
        # detected_by_country no longer resolves (target annexed etc.), so the
        # removal must not be nested inside the `exists = scope:detected_by_country`
        # guard.
        body = _text(EVENTS)
        ev = body[body.index("covert_warfare.1 = {"): body.index("covert_warfare.2 = {")]
        after = ev[ev.index("after = {"):]
        guarded_block = after[: after.index("scope:detected_by_country = {\n\t\t\t\ttrigger_event")]
        self.assertNotIn("remove_variable = iw_burned_type_code", guarded_block)
        self.assertIn(
            "if = {\n\t\t\tlimit = { has_variable = iw_burned_type_code }\n"
            "\t\t\tremove_variable = iw_burned_type_code\n\t\t}",
            after,
        )


class CustomLocTests(unittest.TestCase):
    def test_burned_type_name_matches_the_pinned_codes(self):
        block = _top_level_block(_text(CUSTOM_LOC), "covert_burned_type_name = {")
        for op_type, code in CODES.items():
            pattern = re.compile(
                r"trigger = \{ var:iw_burned_type_code = %d \}\s*"
                r"localization_key = iw_op_name_%s\b" % (code, re.escape(op_type))
            )
            self.assertIsNotNone(
                pattern.search(block),
                f"covert_burned_type_name code {code} is not paired with "
                f"iw_op_name_{op_type}",
            )


class DiplomaticActionTests(unittest.TestCase):
    def test_covert_op_start_calls_pass_the_pinned_code(self):
        body = _text(DIPLOMATIC_ACTIONS)
        for op_type, code in CODES.items():
            pattern = re.compile(
                r"covert_op_start = \{[^}]*TYPE = %s [^}]*CODE = %d[^}]*\}"
                % (re.escape(op_type), code)
            )
            self.assertIsNotNone(
                pattern.search(body),
                f"covert_op_start for {op_type} does not pass CODE = {code}",
            )


class DebugHarnessTests(unittest.TestCase):
    def test_console_event_never_fires_the_detection_event_directly(self):
        body = _text(TE_DEBUG_EVENTS)
        self.assertNotIn("trigger_event = { id = covert_warfare.1 }", body)

    def test_force_detection_calls_the_shipping_roll_effect(self):
        body = _text(TE_DEBUG_EFFECTS)
        self.assertIn("covert_ops_roll_detection_all = yes", body)

    def test_plant_op_calls_pass_the_pinned_code(self):
        body = _text(TE_DEBUG_EFFECTS)
        seed = _top_level_block(body, "te_debug_covert_seed_phases = {")
        for op_type, code in {
            "industrial_espionage": 4,
            "influence_campaign": 6,
            "military_espionage": 5,
        }.items():
            pattern = re.compile(
                r"TYPE = %s\s+ACTION = \S+\s+DEFENSE_MOD = \S+\s+CODE = %d"
                % (re.escape(op_type), code)
            )
            self.assertIsNotNone(
                pattern.search(seed),
                f"te_debug_covert_seed_phases does not pass CODE = {code} for {op_type}",
            )
            self.assertEqual(CODES[op_type], code)


if __name__ == "__main__":
    unittest.main()
