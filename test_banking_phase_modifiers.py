"""The banking cycle's monthly phase modifiers, and the cooperative pool term.

`banking_cycle_apply_phase_modifiers` removes every phase and bubble-inertia
modifier, then adds this month's. A modifier it adds that
`remove_all_banking_phase_modifiers` does not remove is never taken off: the
next month adds another copy, and the journal entry ends up carrying every
phase it has ever been in. The engine says nothing. The cooperative inertia
variants added on 2026-10-05 were the latest names that had to go in both.

The cooperative phases' `country_weekly_investment_pool_mult` is a share of
the pool's weekly gross income. Until 2026-10-05 it multiplied the pool's
balance, which compounded (docs/audits/banking_cycle_simulation.md §21); the
last test keeps it on income.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EFFECTS = ROOT / "common/scripted_effects/banking_cycle_effects.txt"
MODIFIERS = ROOT / "common/static_modifiers/extra_modifiers.txt"
SCRIPT_VALUES = ROOT / "common/script_values/extra_script_values.txt"


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace. Safe because nested closing braces are always
    tab-indented (format_paradox_tabs.py)."""
    block = body[body.index("\n" + header + " = {") + 1:]
    return block[: block.index("\n}") + 2]


def _strip_comments(body):
    return re.sub(r"#[^\n]*", "", body)


class PhaseModifierRemoval(unittest.TestCase):
    def setUp(self):
        effects = _text(EFFECTS)
        self.apply = _strip_comments(_top_level_block(effects, "banking_cycle_apply_phase_modifiers"))
        self.remove = _strip_comments(_top_level_block(effects, "remove_all_banking_phase_modifiers"))

    def test_apply_still_calls_remove_first(self):
        first = self.apply.index("remove_all_banking_phase_modifiers = yes")
        self.assertLess(first, self.apply.index("add_modifier"))

    def test_every_added_modifier_is_removed(self):
        added = set(re.findall(r"add_modifier = \{ name = (\w+)", self.apply))
        removed = set(re.findall(r"remove_modifier = (\w+)", self.remove))
        self.assertGreaterEqual(len(added), 24, "the phase roster shrank; update the floor if deliberate")
        self.assertEqual(added - removed, set(), "added monthly but never removed, so it stacks")

    def test_every_added_modifier_exists(self):
        modifiers = _text(MODIFIERS)
        for name in re.findall(r"add_modifier = \{ name = (\w+)", self.apply):
            self.assertRegex(modifiers, r"(?m)^%s = \{" % name)

    def test_cooperative_inertia_is_a_fifth_of_the_market(self):
        modifiers = _text(MODIFIERS)
        for band in ("moderate", "high", "extreme"):
            market = _top_level_block(modifiers, "bubble_inertia_" + band)
            coop = _top_level_block(modifiers, "bubble_inertia_%s_coop" % band)
            read = lambda b: float(re.search(r"country_finance_momentum_monthly_add = ([\d.]+)", b).group(1))  # noqa: E731
            self.assertAlmostEqual(read(coop), read(market) * 0.2)


class CooperativePoolTerm(unittest.TestCase):
    def test_pool_term_scales_income_not_the_balance(self):
        values = _text(SCRIPT_VALUES)
        body = _strip_comments(_top_level_block(values, "investment_pool_banking_cycle_income_add"))
        lines = [ln.strip() for ln in body.splitlines()[1:] if ln.strip()]
        self.assertEqual(lines[0], "value = investment_pool_gross_income")
        self.assertEqual(lines[1], "min = 0")
        self.assertEqual(lines[2], "multiply = modifier:country_weekly_investment_pool_mult")
        outer = _strip_comments(_top_level_block(values, "investment_pool_banking_cycle_add"))
        self.assertIn("value = investment_pool_banking_cycle_income_add", outer)
        self.assertNotRegex(outer, r"value = investment_pool\s")


if __name__ == "__main__":
    unittest.main()
