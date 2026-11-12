"""The Colonial Empire's three programmes and Investment's expense line are scaling modifiers on je_colonial_empire.

Since 1.15 the entry declares each in `scaling_modifiers_while_active` and the
engine re-reads its value from the owning country about every four days
(design: docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md § 4.5).
Until then the monthly pulse and each step removed and re-added them on the
country, a programme at the literal multipliers 0.333 / 0.667 / 1 and the
expense line at the week's cost. These tests pin each declaration, that its
value gives the old numbers at every level and 0 at level 0 (where the old
refresh added nothing), and that the refresh, the civil-war rebuild and the
pre-levels migration are gone. test_journal_entry_shape.py checks the
tree-wide rule that nothing adds, removes or tests a declared key.
"""

import re
import unittest
from pathlib import Path

from je_multiplier_scope_audit import parse_text
from je_test_helpers import entry_text, outcome_texts

ROOT = Path(__file__).resolve().parent
JE = ROOT / "common/journal_entries/je_colonial_empire.txt"
VALUES = ROOT / "common/script_values/colonial_empire_values.txt"
EFFECTS = ROOT / "common/scripted_effects/decolonization.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_colonial_empire_events.txt"
STATIC = ROOT / "common/static_modifiers/extra_modifiers.txt"

# modifier -> the value its declaration calls
PROGRAMMES = {
    "colonial_development_investment_modifier": ("colonial_invest_modifier_scale", "colonial_invest_level"),
    "colonial_military_garrison_modifier": ("colonial_garrison_modifier_scale", "colonial_garrison_level"),
    "colonial_cultural_assimilation_modifier": ("colonial_assim_modifier_scale", "colonial_assim_level"),
}
EXPENSE = "colonial_development_investment_expense_modifier"
KEYS = {**{m: v for m, (v, _) in PROGRAMMES.items()}, EXPENSE: "colonial_invest_weekly_cost"}
# The literal multipliers colonial_programme_apply_modifier added at levels 1, 2 and 3 before 1.15.
OLD_LADDER = {0: 0, 1: 0.333, 2: 0.667, 3: 1}
BANDS = ("colonial_empire_crumbling_modifier", "colonial_empire_under_pressure_modifier",
         "colonial_empire_strained_modifier", "colonial_empire_stable_modifier",
         "colonial_empire_solidified_modifier")


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace (nested braces are always tab-indented)."""
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}\n") + 3]


def _declarations():
    """modifier -> [value] for every scaling_modifiers_while_active block on the entry. Each value is an inline
    block holding one named script value, `value = { value = <name> }`, the form every vanilla use takes (the
    bare `value = <name>` is unproven): a bare value, or a block that holds anything else, comes back as None."""
    nodes, _ = parse_text(_text(JE), "common/journal_entries/je_colonial_empire.txt")
    entry = next(n for n in nodes if n.key == "je_colonial_empire")
    out = {}
    for block in (c for c in entry.children if c.key == "scaling_modifiers_while_active"):
        modifier = next((c.value for c in block.children if c.key == "modifier"), None)
        value = next((c for c in block.children if c.key == "value"), None)
        inner = None
        if value is not None and value.value is None and len(value.children) == 1:
            only = value.children[0]
            if only.key == "value" and not only.children:
                inner = only.value
        out.setdefault(modifier, []).append(inner)
    return out


def _ladder(block, reads):
    """Evaluate a `value = 0` + `if`/`else_if` chain of `limit = { <reads> >= N } value = X` at each level 0-3."""
    body = _strip_comments(block)
    default = re.search(r"\{\s*value = ([\d.]+)", body)
    steps = re.findall(r"(?:if|else_if) = \{\s*limit = \{ " + re.escape(reads)
                       + r" >= (\d+) \}\s*value = ([\d.]+)\s*\}", body)
    # The chain is the block's whole logic: every if/else_if is one of the steps.
    assert len(re.findall(r"\b(?:if|else_if) = \{", body)) == len(steps), block
    out = {}
    for level in range(4):
        out[level] = float(default.group(1))
        for threshold, value in steps:  # first match wins, as in the engine's if / else_if chain
            if level >= int(threshold):
                out[level] = float(value)
                break
    return out


class DeclarationTests(unittest.TestCase):
    def test_the_entry_declares_exactly_the_four(self):
        # One declaration each, its value the block `value = { value = <name> }`.
        self.assertEqual(_declarations(), {k: [v] for k, v in KEYS.items()})

    def test_each_programme_keeps_the_old_ladder(self):
        values = _text(VALUES)
        for modifier, (value, level) in PROGRAMMES.items():
            with self.subTest(modifier=modifier):
                block = _top_level_block(values, value + " = {")
                self.assertEqual(_ladder(block, level + "_value"), OLD_LADDER)

    def test_the_levels_are_guarded_variable_reads(self):
        # A level the country never stepped does not exist: the value reads 0,
        # so a fresh entry declares nothing. No has_modifier fallback: it could
        # not see a declared copy, and a save from before the levels (2026-10)
        # cannot load in 1.15.
        values = _text(VALUES)
        for _modifier, (_value, level) in PROGRAMMES.items():
            with self.subTest(level=level):
                block = _strip_comments(_top_level_block(values, level + "_value = {"))
                self.assertRegex(block, r"value = 0\s*if = \{\s*limit = \{ has_variable = " + level
                                 + r" \}\s*value = var:" + level + r"\s*\}\s*\}")
                self.assertNotIn("has_modifier", block)

    def test_the_expense_line_is_the_live_weekly_cost(self):
        values = _strip_comments(_text(VALUES))
        weekly = _top_level_block(values, "colonial_invest_weekly_cost = {")
        # One level's cost times the level: 0 at level 0, where the old refresh added nothing.
        self.assertIn("value = colonial_invest_level_cost", weekly)
        self.assertIn("multiply = colonial_invest_level_value", weekly)
        # O(1): the chain reads the monthly cache of the colonies' GDP, never the state walk.
        chain = [weekly, _top_level_block(values, "colonial_invest_level_cost = {"),
                 _top_level_block(values, "colonial_dev_cost_base = {")]
        for block in chain:
            self.assertNotRegex(block, r"\bevery_|\bany_|colonial_development_gdp\b")
        self.assertIn("limit = { has_variable = colonial_dev_colonial_gdp }", chain[2])
        # The cache the value reads still has its writers: the monthly pulse and `immediate`.
        je = _strip_comments(_text(JE))
        self.assertEqual(je.count("colonial_programmes_refresh_cost_base = yes"), 2)

    def test_the_expense_modifier_carries_one_a_unit(self):
        static = _top_level_block(_text(STATIC), EXPENSE + " = {")
        self.assertIn("country_expenses_add = 1", static)
        # The Budget panel's mirror field (gen_budget_breakdown.py's Colonial Development line).
        self.assertIn("country_te_budget_expense_colonial_add = 1", static)

    def test_both_endings_clear_the_levels(self):
        # The levels are the programmes' only state; a later run of the entry
        # starts them at 0 (the entry can come back: ce_reentry_monthly).
        cleanup = _top_level_block(_text(EFFECTS), "colonial_empire_je_cleanup_effect = {")
        for _modifier, (_value, level) in PROGRAMMES.items():
            self.assertIn("remove_variable = " + level, cleanup)
        # Every ending (the nine of #1432, and the invalid outcome on the rule
        # switched off mid-game, 2026-11-08) runs the cleanup, directly or
        # through the success and collapse helpers, which call it.
        effects = _text(EFFECTS)
        for helper in ("colonial_empire_secured_end", "colonial_empire_collapse_end"):
            body = _strip_comments(_top_level_block(effects, helper + " = {"))
            self.assertEqual(body.count("colonial_empire_je_cleanup_effect = yes"), 1, helper)
        entry = entry_text(_text(JE), "je_colonial_empire")
        endings = outcome_texts(entry)
        self.assertEqual(len(endings), 10)
        for i, body in enumerate(endings):
            with self.subTest(outcome=i):
                self.assertEqual(sum(body.count(call + " = yes") for call in (
                    "colonial_empire_je_cleanup_effect", "colonial_empire_secured_end",
                    "colonial_empire_collapse_end")), 1)

    def test_the_bands_stay_on_the_pulse(self):
        # Not converted: Solidified is also the endings' permanent country
        # reward (decol_grant_permanent_modifier), and four bands declared
        # beside one pulse-added band would overlap or gap at the 90 edge.
        declared = _declarations()
        pulse = _strip_comments(_text(JE))
        for band in BANDS:
            with self.subTest(band=band):
                self.assertNotIn(band, declared)
                self.assertIn("je:je_colonial_empire = { add_modifier = { name = %s } }" % band, pulse)


class RefreshGoneTests(unittest.TestCase):
    MODIFIER_OP = re.compile(r"\b(add_modifier|remove_modifier|has_modifier|MODIFIER)\b[^\n]*\b(%s)\b"
                             % "|".join(KEYS))
    GONE = ("colonial_programme_apply_modifier", "colonial_programmes_refresh_modifiers",
            "decol_sync_programmes", "decol_migrate_programme", "colonial_invest_cost_week")

    def test_no_add_remove_or_test_of_the_four(self):
        for path in (JE, EFFECTS, VALUES, DEBUG_EVENTS):
            with self.subTest(path=path.name):
                self.assertEqual(self.MODIFIER_OP.findall(_strip_comments(_text(path))), [])

    def test_the_refresh_the_rebuild_and_the_migration_are_gone(self):
        for path in (JE, EFFECTS, VALUES, DEBUG_EVENTS):
            text = _strip_comments(_text(path))
            for name in self.GONE:
                with self.subTest(path=path.name, name=name):
                    self.assertNotRegex(text, r"\b" + name + r"\b")

    def test_a_step_refreshes_only_the_display(self):
        # The old refresh sat in hidden_effect, so a step's preview was always
        # its core's custom_tooltip (CE_*_UP_TT / _DOWN_TT); it stays.
        effects = _strip_comments(_text(EFFECTS))
        after = _top_level_block(effects, "colonial_programme_after_step = {")
        body = [line.strip() for line in after.splitlines()[1:-1] if line.strip()]
        self.assertEqual(body, ["hidden_effect = {", "colonial_empire_refresh_display = yes", "}"])
        for core in ("invest_up", "invest_down", "garrison_up", "garrison_down",
                     "assimilation_up", "assimilation_down"):
            block = _top_level_block(effects, "colonial_programme_%s = {" % core)
            self.assertIn("text = CE_%s_TT" % core.upper(), block)


class LateCostTests(unittest.TestCase):
    """A Garrison level's authority upkeep reaches the country a few days after the step (the entry declares
    it), so the raise gate counts the levels raised in the last week (review of PR 3, #1404)."""

    def test_the_raise_gate_counts_recent_levels(self):
        triggers = _text(ROOT / "common/scripted_triggers/colonial_empire_triggers.txt")
        gate = _top_level_block(triggers, "colonial_empire_possible_garrison_up = {")
        self.assertIn("authority > colonial_garrison_raise_authority_gate", gate)
        value = _top_level_block(_text(VALUES), "colonial_garrison_raise_authority_gate = {")
        self.assertIn("value = colonial_garrison_authority_per_level", value)
        self.assertIn("value = var:colonial_garrison_pending_levels", value)
        self.assertIn("multiply = colonial_garrison_authority_per_level", value)

    def test_a_player_step_books_the_level(self):
        step = _top_level_block(_text(EFFECTS), "colonial_empire_effect_garrison_up = {")
        self.assertIn("value = { value = var:colonial_garrison_pending_levels add = 1 }", step)
        self.assertIn("set_variable = { name = colonial_garrison_pending_levels value = 1 days = 7 }", step)


if __name__ == "__main__":
    unittest.main()
