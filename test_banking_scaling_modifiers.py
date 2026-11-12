"""The banking cycle's modifiers are scaling modifiers on je_banking_cycle.

Since vanilla 1.15 the entry declares each in `scaling_modifiers_while_active`
and the engine re-reads its value from the owning country about every four
days (design: docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md
§ 4.7). Until then the monthly pulse, every banking event's `after` and the
tool buttons removed and re-added them on the entry. These tests pin the
roster (33 declarations), each value's gate (the cycle runs, the economic law,
the band), the caches three of them read and who writes them, and that the
refresh code is gone. test_banking_phase_modifiers.py holds the phase and
bubble-inertia gates against the old refresh, band by band;
test_banking_external_tools.py runs the two external charges through their
tools; test_journal_entry_shape.py checks the tree-wide rule that nothing
adds, removes or tests a declared key.
"""

import functools
import operator
import re
import unittest
from pathlib import Path

from test_banking_external_tools import definitions as _definitions

ROOT = Path(__file__).resolve().parent
JE = "common/journal_entries/je_banking.txt"
CYCLE_EFFECTS = ROOT / "common/scripted_effects/banking_cycle_effects.txt"
POLICY_EFFECTS = ROOT / "common/scripted_effects/banking_policy_effects.txt"
SCRIPT_VALUES = ROOT / "common/script_values/extra_script_values.txt"
EXTERNAL_VALUES = ROOT / "common/script_values/banking_external_values.txt"
STATIC = ROOT / "common/static_modifiers/extra_modifiers.txt"

PHASES = ("panic", "downturn", "stagnation", "expansion", "boom", "frenzy")
ECONOMIES = {"market": "", "command": "_cmd", "coop": "_coop"}
LAWS = {"command": "law_type:law_command_economy", "coop": "law_type:law_cooperative_ownership"}
FISCAL = "financial_cycle_government_fiscal_policy_effect"
INERTIA = tuple(f"bubble_inertia_{band}{suffix}" for suffix in ("", "_coop")
                for band in ("moderate", "high", "extreme"))
PHASE_KEYS = tuple(f"financial_cycle_phase_{p}{s}" for s in ECONOMIES.values() for p in PHASES)
STANCE = tuple(f"banking_stance_band_{n}" for n in range(1, 6))
POOL = "planning_treasury_pool_balance"
CHARGES = {"banking_external_sterilization_charge": "sterilize_inflows",
           "banking_external_import_charge": "emergency_import_financing"}
ROSTER = (FISCAL,) + INERTIA + PHASE_KEYS + STANCE + (POOL,) + tuple(CHARGES)

# Gone with the refresh (design § 4.0 rule 5): the effects that removed and re-added the keys, and the stance
# band's tracker and its one-time heal.
DELETED = ("banking_cycle_update_fiscal_policy", "banking_cycle_apply_phase_modifiers",
           "remove_all_banking_phase_modifiers", "banking_cycle_apply_stance_band",
           "te_mon_stance_band_applied", "banking_stance_band_healed")
# The old adds' JE-scope multipliers (owner = { } around a country value): kept only for an older save's added
# copies, and gone with the old-save strip (#1429), as 1.15 loads no older save.
RETIRED_WRAPPERS = {
    "financial_cycle_government_fiscal_policy_effect_size_for_je": SCRIPT_VALUES,
    "bubble_inertia_multiplier_script_value": SCRIPT_VALUES,
    "ce_treasury_pool_balance_multiplier_for_je": SCRIPT_VALUES,
    "banking_external_sterilization_weekly_charge_for_je": EXTERNAL_VALUES,
    "banking_external_import_weekly_charge_for_je": EXTERNAL_VALUES,
}

COMPARE = {"=": operator.eq, ">": operator.gt, "<": operator.lt, ">=": operator.ge, "<=": operator.le}


@functools.lru_cache(maxsize=None)
def definitions(path):
    return _definitions(path)


def _text(path):
    return Path(path).read_text(encoding="utf-8-sig")


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first unindented closing brace."""
    block = body[body.index("\n" + header + " = {") + 1:]
    return block[: block.index("\n}") + 2]


def declarations():
    """modifier -> [value body] for every scaling_modifiers_while_active block on je_banking_cycle."""
    entry = definitions(JE)["je_banking_cycle"]
    out = {}
    for key, _, body in entry:
        if key == "scaling_modifiers_while_active":
            fields = dict((k, v) for k, _, v in body)
            out.setdefault(fields.get("modifier"), []).append(fields.get("value"))
    return out


class Country:
    """The owning country a declared value is read from: its variables, its economic law and the tools on its
    entry. A small evaluator over the parsed value; an unknown read fails, and an unguarded missing variable
    raises, as the engine would log."""

    def __init__(self, law="market", tools=(), stubs=None, **variables):
        self.vars = dict(variables)
        self.law = law
        self.tools = set(tools)
        self.stubs = dict(stubs or {})
        self.triggers = definitions("common/scripted_triggers/market_triggers.txt")
        self.values = definitions("common/script_values/extra_script_values.txt")

    def number(self, operand):
        if isinstance(operand, list):
            return self.value(operand)
        if operand.startswith("var:"):
            return self.vars[operand[4:]]
        if operand in self.stubs:
            return self.stubs[operand]
        if operand in self.values:
            return self.value(self.values[operand])
        return float(operand)

    def value(self, body, n=0.0):
        matched = False
        for key, _, operand in body:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    matched = False
                if matched:
                    continue
                limit = next((v for k, _, v in operand if k == "limit"), [])
                if key == "else" or self.check(limit):
                    n = self.value([item for item in operand if item[0] != "limit"], n)
                    matched = True
                continue
            x = self.number(operand)
            n = {"value": lambda: x, "add": lambda: n + x, "subtract": lambda: n - x,
                 "multiply": lambda: n * x, "divide": lambda: n / x,
                 "min": lambda: max(n, x), "max": lambda: min(n, x)}[key]()
        return n

    def check(self, body, mode="AND"):
        answers = []
        for key, op, operand in body:
            if key in ("AND", "OR", "NOT", "NOR"):
                answer = self.check(operand, key)
            elif key == "has_variable":
                answer = operand in self.vars
            elif key == "has_law":
                answer = LAWS.get(self.law) == operand
            elif key.startswith("banking_tool_") and key.endswith("_active"):
                answer = (key[len("banking_tool_"):-len("_active")] in self.tools) == (operand == "yes")
            elif key in self.triggers:
                answer = self.check(self.triggers[key]) == (operand == "yes")
            elif key.startswith("var:"):
                answer = COMPARE[op](self.number(key), self.number(operand))
            else:
                raise AssertionError(f"unsupported trigger {key}")
            answers.append(answer)
            if mode == "AND" and not answer:  # a guarded read short-circuits
                return False
            if mode == "OR" and answer:
                return True
        if mode == "NOT":
            return not any(answers)
        if mode == "NOR":
            return not any(answers)
        return any(answers) if mode == "OR" else all(answers)

    def declared(self, modifier):
        (body,) = declarations()[modifier]
        return self.value(body)


class RosterTest(unittest.TestCase):
    def test_the_entry_declares_exactly_the_cycle_keys(self):
        found = declarations()
        self.assertEqual(sorted(found), sorted(ROSTER))
        for modifier, values in found.items():
            with self.subTest(modifier=modifier):
                self.assertEqual(len(values), 1, "declared twice")

    def test_every_value_is_an_inline_block_off_by_default(self):
        # Vanilla writes every value as a block; each here starts at 0 and adds under one gate.
        for modifier, (body,) in declarations().items():
            with self.subTest(modifier=modifier):
                self.assertIsInstance(body, list)
                self.assertEqual(body[0], ("value", "=", "0"))
                self.assertEqual([k for k, _, _ in body[1:]], ["if"])

    def test_every_declared_modifier_exists(self):
        static = _text(STATIC)
        for modifier in ROSTER:
            with self.subTest(modifier=modifier):
                self.assertRegex(static, r"(?m)^%s = \{" % modifier)

    def test_a_dormant_entry_declares_none_of_the_cycle(self):
        # Every country under the rule holds the entry; until its cycle starts (finance_cycle_value) nothing
        # of the cycle's applies, whatever the other variables hold.
        stubs = {"financial_cycle_government_fiscal_policy_effect_size": 0.7}
        for law in ECONOMIES:
            dormant = Country(law=law, stubs=stubs, bubble_pressure=80, te_mon_stance_band=1,
                              ce_pool_balance_cached=500)
            for modifier in (FISCAL,) + INERTIA + PHASE_KEYS + STANCE + (POOL,):
                with self.subTest(law=law, modifier=modifier):
                    self.assertEqual(dormant.declared(modifier), 0)


class RefreshGoneTest(unittest.TestCase):
    def test_the_refresh_code_is_gone(self):
        deleted = re.compile(r"\b(%s)\b" % "|".join(DELETED))
        for sub in ("common", "events"):
            for path in sorted((ROOT / sub).rglob("*.txt")):
                rel = path.relative_to(ROOT).as_posix()
                text = _strip_comments(_text(path))
                with self.subTest(file=rel):
                    self.assertEqual(sorted(set(deleted.findall(text))), [])

    def test_the_monthly_pulse_keeps_only_the_pool_cache(self):
        je = _strip_comments(_text(ROOT / JE))
        self.assertEqual(je.count("banking_cycle_update_ce_pool_balance = yes"), 1)
        # No stance-band tracker to reset in `immediate` (civil-war audit F7): nothing tracks the bands now.
        immediate = next(body for key, _, body in definitions(JE)["je_banking_cycle"] if key == "immediate")
        self.assertNotIn("stance_band", repr(immediate))

    def test_the_post_event_refresh_clamps_and_draws_the_bars_only(self):
        body = _strip_comments(_top_level_block(_text(CYCLE_EFFECTS), "banking_cycle_post_event_refresh"))
        self.assertNotIn("modifier", body)
        self.assertIn("limit = { ROOT = { te_banking_cycle_running = yes } }", body)
        self.assertEqual(body.count("set_bar_progress"), 6)
        self.assertEqual(body.count("set_variable"), 4)

    def test_the_inertia_curve_is_read_from_the_country(self):
        body = _strip_comments(_top_level_block(_text(SCRIPT_VALUES), "bubble_inertia_curve"))
        self.assertNotIn("owner", body)
        self.assertIn("var:bubble_pressure", body)
        for modifier in INERTIA:
            with self.subTest(modifier=modifier):
                (value,) = declarations()[modifier]
                self.assertIn(("add", "=", "bubble_inertia_curve"), value[1][2])

    def test_the_old_multipliers_are_gone(self):
        found = {}
        for sub in ("common", "events"):
            for path in sorted((ROOT / sub).rglob("*.txt")):
                text = _strip_comments(_text(path))
                for name in RETIRED_WRAPPERS:
                    if re.search(r"\b%s\b" % name, text):
                        found.setdefault(name, []).append(path.relative_to(ROOT).as_posix())
        self.assertEqual(found, {})


class FiscalPolicyTest(unittest.TestCase):
    def test_the_deficit_push_is_declared_live_while_the_cycle_runs(self):
        for size in (-1, -0.25, 0.4, 1):
            running = Country(stubs={"financial_cycle_government_fiscal_policy_effect_size": size},
                              finance_cycle_value=50)
            self.assertEqual(running.declared(FISCAL), size)
        (body,) = declarations()[FISCAL]
        self.assertIn(("add", "=", "financial_cycle_government_fiscal_policy_effect_size"), body[1][2])


class StanceBandTest(unittest.TestCase):
    def test_exactly_the_displayed_band_is_declared(self):
        for band in range(1, 6):
            country = Country(finance_cycle_value=50, te_mon_stance_band=band)
            self.assertEqual([country.declared(m) for m in STANCE], [1 if n == band else 0 for n in range(1, 6)])
        # A cycle whose monetary update has not run yet carries none, as the old swap left it.
        self.assertEqual([Country(finance_cycle_value=50).declared(m) for m in STANCE], [0] * 5)

    def test_band_three_stays_empty(self):
        # Declared at 1 so the entry names the stance; it carries no field (modifier_visibility_audit).
        body = _top_level_block(_strip_comments(_text(STATIC)), "banking_stance_band_3")
        self.assertEqual([ln.strip() for ln in body.splitlines()[1:-1] if ln.strip()],
                         ["icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds"])


class PlanningPoolTest(unittest.TestCase):
    def test_the_balance_is_declared_from_the_cache_under_a_command_economy(self):
        for law in ECONOMIES:
            for cached in (-300.0, 0.0, 1250.0):
                country = Country(law=law, finance_cycle_value=50, ce_pool_balance_cached=cached)
                with self.subTest(law=law, cached=cached):
                    self.assertEqual(country.declared(POOL), cached if law == "command" else 0)
            # No cache yet (an entry before its first pulse, an older save): nothing, and no failed read.
            self.assertEqual(Country(law=law, finance_cycle_value=50).declared(POOL), 0)

    def test_the_cache_keeps_the_monthly_cadence(self):
        effect = _strip_comments(_top_level_block(_text(CYCLE_EFFECTS), "banking_cycle_update_ce_pool_balance"))
        self.assertEqual(" ".join(effect.split()),
                         "banking_cycle_update_ce_pool_balance = { if = { limit = { banking_is_command_economy = yes }"
                         " set_variable = { name = ce_pool_balance_cached value = ce_treasury_pool_balance_multiplier }"
                         " } else_if = { limit = { has_variable = ce_pool_balance_cached }"
                         " set_variable = { name = ce_pool_balance_cached value = 0 } } }")
        # Its writers: the monthly pulse and the two transfers, each of which previews the line.
        policy = _strip_comments(_text(POLICY_EFFECTS))
        for button in ("banking_effect_ce_invest_pool_inject", "banking_effect_ce_invest_pool_withdraw"):
            with self.subTest(button=button):
                body = _top_level_block(policy, button)
                self.assertIn("banking_cycle_update_ce_pool_balance = yes", body)
                self.assertIn("show_as_tooltip = {\n\t\tadd_modifier = { name = planning_treasury_pool_balance "
                              "multiplier = ce_treasury_pool_balance_multiplier }", body)
        values = _strip_comments(_top_level_block(_text(SCRIPT_VALUES), "ce_treasury_pool_balance_multiplier"))
        self.assertIn("subtract = investment_pool_net_income", values)


class ExternalChargeTest(unittest.TestCase):
    def test_each_charge_is_declared_from_its_cache_while_its_tool_is_on(self):
        for modifier, tool in CHARGES.items():
            cache = modifier + "_cached"
            with self.subTest(modifier=modifier):
                self.assertEqual(Country(tools=[tool], **{cache: 42.0}).declared(modifier), 42.0)
                self.assertEqual(Country(**{cache: 42.0}).declared(modifier), 0)    # the winner of a revolution
                self.assertEqual(Country(tools=[tool]).declared(modifier), 0)       # Enabled before 1.15


if __name__ == "__main__":
    unittest.main()
