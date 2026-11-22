"""Covert Warfare's five standing modifiers are scaling modifiers on je_covert_warfare.

Since 1.15 the entry declares each in `scaling_modifiers_while_active` and the
engine re-reads its value from the owning country about every four days
(design: docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md § 4.2).
These tests pin each declaration and its value's "off" gate, which must read 0
wherever the old monthly pulse removed the modifier, and that the refresh code
it replaced is gone. test_journal_entry_shape.py checks the tree-wide rule that
nothing adds, removes or tests a declared key.
"""

import re
import unittest
from pathlib import Path

from je_multiplier_scope_audit import parse_text

ROOT = Path(__file__).resolve().parent
JE = ROOT / "common/journal_entries/je_covert_warfare.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
STATIC = ROOT / "common/static_modifiers/extra_modifiers.txt"
LOC_DIR = ROOT / "localization/english"

KEYS = {
    "intelligence_capacity_defense": "intelligence_capacity_modifier_mult",
    "iw_domestic_defense": "covert_operations_available_slots",
    "iw_funding_defense": "covert_ops_funding_ci_mult",
    "covert_operation_funding_cost": "covert_operation_cost_mult",
    "iw_tradecraft_bonus": "covert_tradecraft_bonus_mult",
}


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace (nested braces are always tab-indented)."""
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}\n") + 3]


def _declarations():
    """modifier -> [value] for every scaling_modifiers_while_active block on the entry."""
    nodes, _ = parse_text(_text(JE), "common/journal_entries/je_covert_warfare.txt")
    entry = next(n for n in nodes if n.key == "je_covert_warfare")
    out = {}
    for block in (c for c in entry.children if c.key == "scaling_modifiers_while_active"):
        fields = {c.key: c for c in block.children}
        value = fields.get("value")
        # Written as vanilla does, an inline block: value = { value = <name> }.
        inner = [c.value for c in value.children if c.key == "value"] if value is not None and value.children else []
        out.setdefault(fields.get("modifier").value, []).append(inner[0] if len(inner) == 1 else None)
    return out


class DeclarationTests(unittest.TestCase):
    def _assert_declared(self, modifier):
        self.assertEqual(_declarations().get(modifier), [KEYS[modifier]],
                         "%s: one declaration, value { value = %s }" % (modifier, KEYS[modifier]))

    def test_the_entry_declares_exactly_the_five(self):
        self.assertEqual({k: v[0] for k, v in _declarations().items()}, KEYS)

    def test_intelligence_capacity_defense(self):
        self._assert_declared("intelligence_capacity_defense")
        block = _top_level_block(_text(VALUES), "intelligence_capacity_modifier_mult = {")
        # The old pulse removed it below 1 total capacity, where IC / 25 is not yet 0.
        self.assertIn("limit = { intelligence_capacity_total >= 1 }", block)
        self.assertIn("divide = 25", block)
        self.assertIn("min = 0", block)
        self.assertIn("max = 5", block)

    def test_iw_domestic_defense(self):
        self._assert_declared("iw_domestic_defense")
        block = _top_level_block(_text(VALUES), "covert_operations_available_slots = {")
        # Whole slots floored at 0: 0 exactly where the old `>= 1` gate removed it.
        self.assertIn("add = covert_operation_max_slots", block)
        self.assertIn("subtract = covert_operation_slots_used", block)
        self.assertIn("min = 0", block)

    def test_iw_funding_defense(self):
        self._assert_declared("iw_funding_defense")
        block = _top_level_block(_text(VALUES), "covert_ops_funding_ci_mult = {")
        # Funding level - 1, guarded and floored: 0 at levels 0 and 1.
        self.assertIn("limit = { has_variable = iw_funding_level }", block)
        self.assertIn("subtract = 1", block)
        self.assertIn("min = 0", block)

    def test_covert_operation_funding_cost(self):
        self._assert_declared("covert_operation_funding_cost")
        block = _top_level_block(_text(VALUES), "covert_operation_cost_mult = {")
        # Multiplied by the guarded funding level: 0 at funding 0.
        self.assertRegex(block, r"multiply = \{\s*value = 0\s*if = \{\s*limit = \{ has_variable = iw_funding_level \}"
                                r"\s*add = var:iw_funding_level")
        self.assertIn("min = 0", block)
        # The Budget panel's mirror field, which the scaling_inherited self-check reads.
        static = _top_level_block(_text(STATIC), "covert_operation_funding_cost = {")
        self.assertIn("country_te_budget_expense_covert_add = 1", static)
        self.assertIn("country_expenses_add = 1", static)

    def test_iw_tradecraft_bonus(self):
        self._assert_declared("iw_tradecraft_bonus")
        block = _top_level_block(_text(VALUES), "covert_tradecraft_bonus_mult = {")
        self.assertIn("add = covert_tradecraft_tier", block)
        # The tier's four triggers guard the variable: 0 for a country without one.
        triggers = _text(TRIGGERS)
        for n in range(1, 5):
            tier = _top_level_block(triggers, "covert_tradecraft_tier_%d = {" % n)
            self.assertIn("has_variable = iw_tradecraft", tier)


class RefreshGoneTests(unittest.TestCase):
    MODIFIER_OP = re.compile(r"\b(add_modifier|remove_modifier|has_modifier)\b[^\n]*\b(%s)\b" % "|".join(KEYS))

    def test_no_add_remove_or_test_of_the_five(self):
        for path in (JE, EFFECTS, DEBUG_EFFECTS):
            with self.subTest(path=path.name):
                self.assertEqual(self.MODIFIER_OP.findall(_text(path)), [])

    def test_the_pulse_and_the_tradecraft_refresh_are_gone(self):
        self.assertNotIn("je:je_covert_warfare = {", _text(JE))
        for path in (EFFECTS, DEBUG_EFFECTS):
            self.assertNotIn("covert_tradecraft_refresh_bonus", _text(path), path.name)

    def test_funding_refresh_is_a_shell_that_still_syncs(self):
        # covert_apply_priority_change and the steppers still call it
        # (test_covert_priority.py); what is left is the detection re-stage.
        block = _top_level_block(_text(EFFECTS), "covert_refresh_funding_state = {")
        body = [line.strip() for line in block.splitlines()[1:-1] if line.strip()]
        self.assertEqual(body, ["covert_ops_sync_all = yes"])

    def test_steppers_keep_their_cost_preview(self):
        # The old add sat in hidden_effect, so a stepper's preview was always its
        # custom_tooltip naming the new weekly cost; it stays.
        effects = _text(EFFECTS)
        loc = "".join(p.read_text(encoding="utf-8-sig") for p in LOC_DIR.rglob("*.yml"))
        for direction, value in (("increase", "up"), ("decrease", "down")):
            block = _top_level_block(effects, "covert_effect_%s_funding = {" % direction)
            self.assertIn("custom_tooltip = iw_%s_funding_effect_tt" % direction, block)
            self.assertIn("covert_refresh_funding_state = yes", block)
            line = re.search(r"(?m)^ iw_%s_funding_effect_tt:0 (.*)$" % direction, loc).group(1)
            self.assertIn("covert_operation_cost_at_next_%s" % value, line)


if __name__ == "__main__":
    unittest.main()
