"""The banking cycle's phase and bubble-inertia modifiers, and the cooperative pool term.

Since vanilla 1.15 (#1404) je_banking_cycle declares the 18 phase modifiers
and the six bubble-inertia tiers (scaling_modifiers_while_active) instead of
`banking_cycle_apply_phase_modifiers` removing all 24 and adding this month's,
every month and after every banking event. The old pair had to agree on the
roster: a modifier the apply added that the remove did not take off stacked a
copy a month. A declaration has nothing to take off; what it must keep is the
old gate. These tests run each declaration over a grid of cycle values, bubble
pressures and economies and compare it with that refresh (OLD_PHASE,
OLD_INERTIA, transcribed from it), edge by edge.

The cooperative phases' `country_weekly_investment_pool_mult` is a share of
the pool's weekly gross income. Until 2026-10-05 it multiplied the pool's
balance, which compounded (docs/audits/banking_cycle_simulation.md §21); the
last test keeps it on income.
"""

import re
import unittest
from pathlib import Path

from test_banking_scaling_modifiers import ECONOMIES, INERTIA, PHASE_KEYS, PHASES, Country

ROOT = Path(__file__).resolve().parent
MODIFIERS = ROOT / "common/static_modifiers/extra_modifiers.txt"
SCRIPT_VALUES = ROOT / "common/script_values/extra_script_values.txt"
CYCLE_EDGES = (10, 25, 40, 60, 75, 88)
BUBBLE_EDGES = (0.5, 15, 35, 50, 65)


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


def _around(edges, top):
    """Each edge, just under and just over it, and a coarse sweep."""
    points = {0, top}
    for e in edges:
        points.update((e - 0.01, e, e + 0.01))
    points.update(range(0, top + 1, 5))
    return sorted(p for p in points if 0 <= p <= top)


def OLD_PHASE(cycle, economy):
    """The phase modifier banking_cycle_apply_phase_modifiers added: none in Stable."""
    for edge, phase in zip(CYCLE_EDGES, ("panic", "downturn", "stagnation", None, "expansion", "boom")):
        if cycle < edge:
            break
    else:
        phase = "frenzy"
    return None if phase is None else f"financial_cycle_phase_{phase}{ECONOMIES[economy]}"


def OLD_INERTIA(bubble, economy):
    """The inertia tier it added: by band, the _coop set under Cooperative Ownership, none under command."""
    if economy == "command" or bubble <= 0.5:
        return None
    band = "extreme" if bubble >= 65 else "high" if bubble >= 35 else "moderate"
    return f"bubble_inertia_{band}{'_coop' if economy == 'coop' else ''}"


def CURVE(bubble):
    """bubble_inertia_curve as its comment states it."""
    if bubble <= 15:
        return 0.0
    if bubble < 50:
        return (bubble - 15) * 0.25 / 35
    return 0.25 + 0.005 * (bubble - 50) - 0.00002 * (bubble - 50) ** 2


class PhaseDeclarations(unittest.TestCase):
    def test_each_phase_is_declared_in_its_band_and_economy(self):
        for economy in ECONOMIES:
            for cycle in _around(CYCLE_EDGES, 100):
                country = Country(law=economy, finance_cycle_value=cycle, bubble_pressure=0)
                on = {m for m in PHASE_KEYS if country.declared(m)}
                with self.subTest(economy=economy, cycle=cycle):
                    expected = OLD_PHASE(cycle, economy)
                    self.assertEqual(on, {expected} if expected else set())
                    self.assertTrue(all(country.declared(m) in (0, 1) for m in PHASE_KEYS))

    def test_every_phase_is_reached(self):
        reached = {OLD_PHASE(c, e) for e in ECONOMIES for c in _around(CYCLE_EDGES, 100)} - {None}
        self.assertEqual(reached, set(PHASE_KEYS))
        self.assertEqual(len(PHASE_KEYS), 3 * len(PHASES))


class InertiaDeclarations(unittest.TestCase):
    def test_each_tier_is_the_curve_in_its_band_and_economy(self):
        for economy in ECONOMIES:
            for bubble in _around(BUBBLE_EDGES, 100):
                country = Country(law=economy, finance_cycle_value=50, bubble_pressure=bubble)
                values = {m: country.declared(m) for m in INERTIA}
                expected = OLD_INERTIA(bubble, economy)
                with self.subTest(economy=economy, bubble=bubble):
                    for modifier, value in values.items():
                        self.assertAlmostEqual(value, CURVE(bubble) if modifier == expected else 0, places=9)

    def test_the_curve_is_the_old_multiplier_read_from_the_country(self):
        country = Country(bubble_pressure=0)
        for bubble in _around(BUBBLE_EDGES, 100):
            country.vars["bubble_pressure"] = bubble
            with self.subTest(bubble=bubble):
                self.assertAlmostEqual(country.number("bubble_inertia_curve"), CURVE(bubble),
                                       places=9)
        self.assertAlmostEqual(CURVE(100), 0.45)

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
