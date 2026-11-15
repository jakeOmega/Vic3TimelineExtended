"""What switching a banking intervention on and off again costs.

The owner's rule (2026-11-14): every intervention but Moral Suasion costs
something for a round trip, so none can be clicked back and forth for free,
and the cost is small and the same for every routine tool: 0.5% of pops
radicalized (`banking_toggle_radicals_value`), or 0.2% of GDP for the lending
tools (`banking_toggle_treasury_cost`), paid on switching on. A tool that
grants loyalists on one switch radicalizes the same pops by the grant plus the
friction on the other (`banking_toggle_paired_radicals_value`), so it nets the
same. The command and cooperative economies follow the same rule, their
1-point tools exempt for Moral Suasion's reason. The crisis programs keep a
price of their own, which must still be a cost, and Capital Controls
pays in infamy. Until then the five External & Currency tools and most of the
planning and council tools were free both ways, the leaning tools cost 4% a
round trip and the deposit guarantee 1%, and two council tools gained
loyalists once in five years.

Every tool is read from `banking_policy_effects.txt`'s enable/disable pairs,
so a new tool is held to the routine rule the moment its effects exist.
"""

import re
import unittest
from pathlib import Path

import test_banking_tool_roster as roster

ROOT = Path(__file__).resolve().parent
EFFECTS = ROOT / "common/scripted_effects/banking_policy_effects.txt"
VALUES = ROOT / "common/script_values/extra_script_values.txt"
GUIDE = ROOT / "docs/player_guide/04-banking.md"

# Free to switch by design: a 1-point tool the AI lifts to free its point.
EXEMPT = {"cb_moral_suasion", "ce_coordination_protocol", "cw_solidarity_campaign", "cw_council_directive"}
# Used once per crisis; their one-off price is the program's own cost.
CRISIS = {"cb_asset_relief_program", "cb_bail_in_regime", "cb_bank_holiday", "cb_emergency_liquidity_program"}
# Pays in infamy and great-power relations.
INFAMY = {"cb_capital_controls_outflow"}
# Routine tools whose friction is the treasury's; every other routine tool's is radicals.
LENDING = {
    "cb_open_market_ops",
    "cb_export_credit_facility",
    "cb_directed_credit_infrastructure",
    "cb_directed_credit_heavy_industry",
    "cb_directed_credit_agriculture",
    "cb_directed_credit_armaments",
    "cb_directed_credit_electrification",
}
# Command-economy actions with no on/off state.
TRANSFERS = {"ce_invest_pool_inject", "ce_invest_pool_withdraw"}

FRICTION_NAMES = ("banking_toggle_radicals_value", "banking_toggle_paired_radicals_value", "banking_toggle_treasury_cost")


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _values():
    """Every script value in the file as a number, a GDP-scaled value as its
    share of GDP (`value = gdp` counts as 1)."""
    text = _text(VALUES)
    raw = dict(re.findall(r"(?m)^(\w+) = ([-\d.]+)\s*$", text))
    blocks = dict(re.findall(r"(?ms)^(\w+) = \{\n(.*?)^\}", text))
    cache = {}

    def term(token):
        if token in ("gdp", "root.gdp"):
            return 1.0
        if re.fullmatch(r"-?[\d.]+", token):
            return float(token)
        return resolve(token)

    def resolve(name):
        if name in cache:
            return cache[name]
        if name in raw:
            cache[name] = float(raw[name])
            return cache[name]
        if name not in blocks:
            raise AssertionError("%s is not a script value in %s" % (name, VALUES.name))
        body = blocks[name]
        total = None
        for op, token in re.findall(r"(?m)^\t(value|add|subtract|multiply) = (\S+)", body):
            x = term(token)
            if op == "value":
                total = x
            elif op == "add":
                total += x
            elif op == "subtract":
                total -= x
            else:
                total *= x
        cache[name] = total
        return total

    return resolve


def _effects():
    return dict(re.findall(r"(?ms)^(banking_effect_\w+) = \{\n(.*?)^\}", _text(EFFECTS)))


def _pairs():
    """tool -> (enable body, disable body), for every pair in the effects file."""
    effects = _effects()
    pairs = {}
    for name, body in effects.items():
        m = re.fullmatch(r"banking_effect_(c[bew])_(?!disable_)(\w+)", name)
        if not m:
            continue
        off = "banking_effect_%s_disable_%s" % m.groups()
        if off in effects:
            pairs["%s_%s" % m.groups()] = (body, effects[off])
    return pairs


class Side:
    """The one-off costs a single effect charges, at its top level."""

    def __init__(self, body, value):
        self.radicals, self.loyalists = {}, {}
        for kind, store in (("radicals", self.radicals), ("loyalists", self.loyalists)):
            for name, strata in re.findall(r"(?m)^\tadd_%s = \{ value = (\w+)(?: strata = (\w+))? \}$" % kind, body):
                key = strata or "all"
                store[key] = store.get(key, 0.0) + value(name)
        self.treasury = sum(value(n) for n in re.findall(r"(?m)^\tadd_treasury = (\w+)$", body))
        self.infamy = sum(float(n) for n in re.findall(r"(?m)^\tchange_infamy = \{ value = ([-\d.]+) \}$", body))
        self.body = body

    def empty(self):
        return not (self.radicals or self.loyalists or self.treasury or self.infamy)

    def nested_costs(self):
        """Cost lines below the top level, which would only sometimes be paid."""
        return re.findall(r"(?m)^\t\t+(add_radicals|add_loyalists|add_treasury|change_infamy)\b", self.body)


def _round_trip(on, off):
    """Net radicals by stratum (loyalists count against them) and net treasury."""
    net = {}
    for side in (on, off):
        for k, x in side.radicals.items():
            net[k] = net.get(k, 0.0) + x
        for k, x in side.loyalists.items():
            net[k] = net.get(k, 0.0) - x
    return {k: x for k, x in net.items() if abs(x) > 1e-9}, on.treasury + off.treasury


class ToggleCostTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = staticmethod(_values())
        cls.pairs = {t: (Side(a, cls.value), Side(b, cls.value)) for t, (a, b) in _pairs().items()}
        cls.radicals = cls.value("banking_toggle_radicals_value")
        cls.paired = cls.value("banking_toggle_paired_radicals_value")
        cls.grant = cls.value("banking_small_radicals_value")
        cls.treasury = cls.value("banking_toggle_treasury_cost")

    def test_every_tool_is_read(self):
        # The JE's market tools and the alternate economies' buttons, less the transfers.
        alt = re.findall(r"(?m)^(c[ew]_(?!disable_)\w+) = \{", roster._text(roster.ALT_BUTTONS))
        expected = set(roster._tools()) | (set(alt) - TRANSFERS)
        self.assertEqual(set(self.pairs), expected)
        for group in (EXEMPT, CRISIS, INFAMY, LENDING):
            self.assertLessEqual(group, set(self.pairs))

    def test_exempt_tools_are_the_ungated_ones(self):
        # The AI lifts these whenever another tool wants the point, with no hold
        # gate, because switching them costs nothing (test_banking_tool_roster).
        self.assertEqual(EXEMPT, roster.UNGATED_DISABLES | roster.UNGATED_ALT_DISABLES)
        for tool in EXEMPT:
            with self.subTest(tool=tool):
                on, off = self.pairs[tool]
                self.assertTrue(on.empty() and off.empty(), "%s should be free to switch" % tool)

    def test_every_round_trip_costs_something(self):
        for tool, (on, off) in self.pairs.items():
            if tool in EXEMPT:
                continue
            with self.subTest(tool=tool):
                net, treasury = _round_trip(on, off)
                self.assertTrue(
                    any(x > 0 for x in net.values()) or treasury < 0 or on.infamy + off.infamy > 0,
                    "%s: switching it on and off again costs nothing" % tool,
                )
                self.assertFalse(any(x < 0 for x in net.values()), "%s: a round trip gains loyalists %r" % (tool, net))

    def test_routine_tools_cost_one_unit(self):
        for tool, (on, off) in self.pairs.items():
            if tool in EXEMPT | CRISIS | INFAMY:
                continue
            with self.subTest(tool=tool):
                self.assertEqual(on.nested_costs() + off.nested_costs(), [], "a conditional cost is not always paid")
                net, treasury = _round_trip(on, off)
                if tool in LENDING:
                    self.assertEqual(net, {})
                    self.assertAlmostEqual(treasury, self.treasury)
                    self.assertAlmostEqual(on.treasury, self.treasury, msg="paid on switching on")
                    self.assertIn("banking_toggle_treasury_cost", on.body)
                    continue
                self.assertEqual(treasury, 0)
                self.assertEqual(len(net), 1, "one stratum pays: %r" % net)
                self.assertAlmostEqual(next(iter(net.values())), self.radicals)
                granting = on if on.loyalists else off if off.loyalists else None
                if granting is None:
                    self.assertEqual(off.radicals, {}, "an unpaired tool pays on switching on")
                    self.assertIn("banking_toggle_radicals_value", on.body)
                    continue
                paying = off if granting is on else on
                self.assertEqual(granting.radicals, {})
                self.assertEqual(set(granting.loyalists), set(paying.radicals), "the same pops")
                self.assertAlmostEqual(sum(granting.loyalists.values()), self.grant)
                self.assertIn("banking_toggle_paired_radicals_value", paying.body)

    def test_crisis_programs_keep_their_own_price(self):
        # Their price is the program's cost, not the shared friction, so
        # retuning the friction must not move it.
        for tool in CRISIS:
            with self.subTest(tool=tool):
                on, off = self.pairs[tool]
                for name in FRICTION_NAMES:
                    self.assertNotIn(name, on.body + off.body)

    def test_capital_controls_pay_infamy(self):
        for tool in INFAMY:
            on, off = self.pairs[tool]
            self.assertGreater(on.infamy, 0)
            self.assertTrue(off.empty())

    def test_guide_quotes_the_friction(self):
        # 04-banking.md states both figures; change it with them.
        self.assertAlmostEqual(self.radicals, 0.005)
        self.assertAlmostEqual(self.treasury, -0.002)
        guide = _text(GUIDE)
        self.assertIn("0.5% of pops", guide)
        self.assertIn("0.2% of GDP", guide)


if __name__ == "__main__":
    unittest.main()
