"""Structural regression test for the covert per-operation detection roll
(spec: docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md,
slice 1).

The engine cannot be run in CI, so these tests pin the *shape* of the script
the slice changed: the pulse rolls per operation through one named effect, the
old country-level roll and its target_max_ic restore block are gone, the
detection event is driven by scope:iw_burned_op, and every sync row carries a
type code. A refactor that silently re-introduces the single roll, or drops a
CODE from one of the nine rows, fails here rather than in a play test.

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

OP_TYPES = [
    "election_interference",
    "financial_subversion",
    "infrastructure_sabotage",
    "comms_disruption",
    "industrial_espionage",
    "military_espionage",
    "influence_campaign",
    "ideological_subversion",
    "destabilization",
]


def _parse(path):
    p = ParadoxFileParser()
    p.parse_file(str(path), apply_directives=False)
    return p.data


def _val(node):
    """The parser stores every field as an ('=', value) tuple; unwrap one."""
    return node[1] if isinstance(node, tuple) else node


def _text(path):
    return path.read_text(encoding="utf-8-sig")


class RollEffectTests(unittest.TestCase):
    def test_roll_effect_is_defined_and_rolls_per_container(self):
        data = _parse(EFFECTS)
        self.assertIn("covert_ops_roll_detection_all", data)
        body = _text(EFFECTS)
        block = body[body.index("covert_ops_roll_detection_all = {"):]
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
        self.assertIn("covert_ops_detection_multi_op_scale", data)
        sv = _val(data["covert_op_roll_chance"])
        self.assertEqual(_val(sv["value"]), "var:iw_detect")
        self.assertEqual(_val(sv["multiply"]), "covert_ops_detection_multi_op_scale")

    def test_every_sync_row_passes_a_distinct_code(self):
        body = _text(EFFECTS)
        block = body[body.index("covert_ops_sync_all = {"):]
        block = block[: block.index("\n}\n") + 3]
        codes = {}
        for t in OP_TYPES:
            m = re.search(
                r"covert_op_sync = \{[^}]*TYPE = %s [^}]*CODE = (\d+)" % re.escape(t),
                block,
            )
            self.assertIsNotNone(m, f"no CODE on the {t} sync row")
            codes[t] = int(m.group(1))
        self.assertEqual(sorted(codes.values()), list(range(9)))
        # The codes must match covert_last_exposed_type_name's mapping.
        self.assertEqual(codes["election_interference"], 0)
        self.assertEqual(codes["destabilization"], 8)
        sync = body[body.index("covert_op_sync = {"):]
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


if __name__ == "__main__":
    unittest.main()
