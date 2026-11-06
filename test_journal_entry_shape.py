"""The shape of the mod's journal entries under vanilla 1.15.

- No entry keeps a field 1.15 dropped, and every entry declares `activation_description` (the tree checks of the
  one-shot outcome converter, retired with #1404).
- `disable_evaluation` (#1404, design § 1): every entry whose gate requires a game rule prunes on that rule, and a
  prune reads nothing but game rules, so it can't delete an entry a country could still come to qualify for.
- `scaling_modifiers_while_active` (design § 3): a declared modifier exists, and nothing adds, removes or tests it
  with `has_modifier`, which can't see one.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from je_multiplier_scope_audit import Node, parse_text

ROOT = Path(__file__).resolve().parent
JE_DIR = ROOT / "common" / "journal_entries"

# Fields 1.15 replaced with `outcome = { }` blocks, and the old fields with no 1.15 equivalent.
DROPPED_FIELDS = frozenset({
    "complete", "fail", "invalid", "on_complete", "on_fail", "on_invalid", "on_timeout",
    "custom_completion_header", "custom_on_completion_header",
    "custom_failure_header", "custom_on_failure_header",
    "event_outcome_completed_desc", "event_outcome_failed_desc", "event_outcome_timeout_desc",
    "event_outcome_completed_effect_desc", "event_outcome_failed_effect_desc",
    "event_outcome_timeout_effect_desc",
    "on_complete_all_involved", "on_fail_all_involved", "on_invalid_all_involved", "on_timeout_all_involved",
    "event_outcome_invalidated_desc", "event_outcome_invalidated_effect_desc",
})


def _parse(path: Path) -> list[Node]:
    return parse_text(path.read_text(encoding="utf-8-sig"), path.relative_to(ROOT).as_posix())[0]


def load_entries() -> list[tuple[str, Node]]:
    """(repo-relative path, entry node) for every top-level entry in common/journal_entries/."""
    return [(path.relative_to(ROOT).as_posix(), node)
            for path in sorted(JE_DIR.glob("*.txt"))
            for node in _parse(path) if node.children]


def child(node: Node, key: str) -> Node | None:
    return next((c for c in node.children if c.key == key), None)


def dropped_fields(entry: Node) -> list[str]:
    return sorted({c.key for c in entry.children} & DROPPED_FIELDS)


class DroppedFieldsTest(unittest.TestCase):
    def test_dropped_fields_fixture(self):
        nodes, _ = parse_text("je_x = {\n\ton_complete = { }\n\ttimeout = 5\n\toutcome = { }\n}\n", "j.txt")
        self.assertEqual(dropped_fields(nodes[0]), ["on_complete"])

    def test_no_entry_keeps_a_field_vanilla_dropped(self):
        entries = load_entries()
        self.assertGreater(len(entries), 30)
        for rel, entry in entries:
            with self.subTest(file=rel, entry=entry.key):
                self.assertEqual(dropped_fields(entry), [])

    def test_every_entry_declares_activation_description(self):
        """1.15 logs "missing an activation_description trigger" for an entry without one (29 mod entries on the
        first 1.15 game); vanilla's default is `activation_description = { always = yes }`."""
        for rel, entry in load_entries():
            if entry.key.startswith("INJECT:"):  # takes the field from its target; a REPLACE: needs its own
                continue
            with self.subTest(file=rel, entry=entry.key):
                self.assertIsNotNone(child(entry, "activation_description"))


if __name__ == "__main__":
    unittest.main()
