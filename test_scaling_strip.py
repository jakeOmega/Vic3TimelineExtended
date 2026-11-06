# -*- coding: utf-8 -*-
"""The old-save strip of 1.15's scaling modifiers runs within a week of a load (#1404).

A save made before a system's conversion still holds the copies its old pulse added, which stack with the entry's
declarations until `legacy_je_modifier_cleanup_effect` removes them. That runs monthly, so each system's part is its
own `legacy_scaling_strip_<system>` effect, which the system's entry also runs from its weekly pulse (review of PR 4:
up to a month of doubled banking phases). These tests hold every declaring entry to that shape. Delete with the strip
(after 2026-12-31).
"""

from __future__ import annotations

import unittest
from pathlib import Path

from je_multiplier_scope_audit import Node, parse_text

ROOT = Path(__file__).resolve().parent
JE_DIR = ROOT / "common" / "journal_entries"
LEGACY = ROOT / "common" / "scripted_effects" / "legacy_modifier_cleanup.txt"
PREFIX = "legacy_scaling_strip_"
# An entry added after the conversion holds no old copies of its own: an old save's copies of what it declares sit on
# the entry that used to declare it, whose weekly strip removes them. New entry -> that entry.
MOVED_FROM = {"je_world_climate": "je_global_warming"}  # Climate Warming (#1448)


def _parse(path: Path) -> list[Node]:
    return parse_text(path.read_text(encoding="utf-8-sig"), path.relative_to(ROOT).as_posix())[0]


def _walk(nodes):
    for node in nodes:
        yield node
        yield from _walk(node.children)


def _child(node: Node, key: str) -> Node | None:
    return next((c for c in node.children if c.key == key), None)


def _declaring_entries() -> dict[str, tuple[Node, set[str]]]:
    """entry key -> (the bare entry, the modifiers it declares). An `INJECT:<entry>` block's declarations
    (Space Race's generated sr_sites_generated.txt) count towards the entry it merges into."""
    bare, declared = {}, {}
    for path in sorted(JE_DIR.glob("*.txt")):
        for entry in _parse(path):
            key = entry.key.split(":", 1)[1] if ":" in entry.key else entry.key
            if ":" not in entry.key:
                bare[key] = entry
            names = {_child(b, "modifier").value for b in entry.children
                     if b.key == "scaling_modifiers_while_active" and _child(b, "modifier") is not None}
            if names:
                declared.setdefault(key, set()).update(names)
    return {key: (bare[key], names) for key, names in declared.items()}


def _strip_effects() -> dict[str, Node]:
    return {n.key: n for n in _parse(LEGACY) if n.key.startswith(PREFIX)}


def _removed(effect: Node) -> set[str]:
    return {n.value for n in _walk(effect.children) if n.key == "remove_modifier" and not n.children}


class StripShapeTest(unittest.TestCase):
    def test_every_declaring_entry_strips_its_keys_weekly(self):
        effects = _strip_effects()
        entries = _declaring_entries()
        bare = {e.key: e for path in sorted(JE_DIR.glob("*.txt")) for e in _parse(path) if ":" not in e.key}
        for key, (entry, declared) in entries.items():
            with self.subTest(entry=key):
                if key in MOVED_FROM:
                    entry = bare[MOVED_FROM[key]]
                weekly = _child(entry, "on_weekly_pulse")
                self.assertIsNotNone(weekly, "no on_weekly_pulse to run the strip from")
                calls = {n.key for n in _walk(weekly.children) if n.key.startswith(PREFIX) and n.value == "yes"}
                self.assertEqual(len(calls), 1, f"weekly pulse calls {sorted(calls)}")
                (call,) = calls
                self.assertIn(call, effects, f"{call} is not defined in {LEGACY.name}")
                self.assertEqual(sorted(declared - _removed(effects[call])), [],
                                 f"{call} leaves these declared keys' old copies")

    def test_a_moved_declaration_is_new_on_its_entry(self):
        """The exemption is for an entry that never held an added copy: it runs no strip of its own."""
        entries = _declaring_entries()
        for key in MOVED_FROM:
            with self.subTest(entry=key):
                self.assertIn(key, entries)
                self.assertIsNone(_child(entries[key][0], "on_weekly_pulse"))

    def test_the_monthly_strip_runs_every_system(self):
        cleanup = next(n for n in _parse(LEGACY) if n.key == "legacy_je_modifier_cleanup_effect")
        called = {n.key for n in cleanup.children if n.key.startswith(PREFIX) and n.value == "yes"}
        self.assertEqual(called, set(_strip_effects()))

    def test_banking_seeds_its_caches_before_the_copies_go(self):
        body = (LEGACY.read_text(encoding="utf-8-sig")
                .split(f"{PREFIX}banking_cycle = {{", 1)[1].split("\n}\n", 1)[0])
        for modifier, seed in (("planning_treasury_pool_balance", "banking_cycle_update_ce_pool_balance = yes"),
                               ("banking_external_sterilization_charge", "banking_external_charge_sterilization = yes"),
                               ("banking_external_import_charge", "banking_external_charge_import = yes")):
            with self.subTest(modifier=modifier):
                self.assertLess(body.index(seed), body.index(f"remove_modifier = {modifier} }}"))


if __name__ == "__main__":
    unittest.main()
