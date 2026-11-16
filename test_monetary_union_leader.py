# -*- coding: utf-8 -*-
"""What the Monetary Union's tiers hand the bloc's leader (2026-11-14).

monetary_policy_design.md §0.14. The leader of a bloc whose common currency a
member has adopted (the issuer) shares the adopters' three managed modifiers,
earns seigniorage and a cut of risk premium in proportion to its currency's
reach, runs more banking interventions at once, and shares a common capital
market with its adopters. All of it is script, applied by step 9b of the
monthly monetary update, so the engine checks none of it: a gate that stops
short of the top tier, a term that outlives its condition or a tooltip figure
that drifts from the script value is silent in the game.

These tests run the real script. ``Script`` is a small interpreter over the
parsed files: unknown syntax fails instead of passing, so a changed gate has to
be taught to the test before it can go unseen.

* every tier gate lists every higher tier, and every per-tier figure is the
  tier's own constant, never a lower tier's;
* the issuer test: each of its four conditions takes every benefit away;
* reach, seigniorage and the premium cut against worked figures, the owner's
  1957 Singapore among them, and their limits;
* the interventions and the banking union stop at Unregulated Banking;
* for an adopter as for the issuer (#1812, ``RegulatorTest``): no grant of intervention points
  reaches a country under that law, and its Monetary Union row says why;
* the common capital market by tier, the same in every phase of the cycle
  (owner, 2026-11-14: nothing here may soften a downturn or a panic), and
  nothing on a pool that cannot be spent;
* step 9b applied end to end: the modifiers go on, follow the tier, and come
  off the pulse the leader stops qualifying;
* the principle's display fields and the loc's figures against the script.

After the independent review of PR #1810 (2026-11-14):

* reach asks for the issuer at every tier: a tier V leader with treaty peggers
  and no adopter is paid nothing, and the last adopter's exit takes seigniorage
  and the cut off with a pegger still anchored;
* each scaled modifier's one field and unit are literals here, and each has a
  tracker no other modifier shares (three mutations had survived);
* the self-check's mark is cleared when the leader stops qualifying, run with
  the engine's rule that a pulse cannot see the modifiers it added;
* the seigniorage is a flat minting add, so the leader's minting bonuses
  multiply it: every stated figure is "before minting bonuses", and the bonuses
  the guide names and the ceiling the tooltip gives are the laws', the
  technologies' and the inflation bands' own (``MintingBonusTest``).

2026-11-15 (owner: the principle's lines read as paragraphs): every figure the
principle prints is a numeric display field, each held here to the script
value or static modifier that pays it (``TooltipTest``).
"""

import math
import operator
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
OPERATORS = {"=", "?=", "<", ">", "<=", ">=", "!="}
COMPARE = {"=": operator.eq, "?=": operator.eq, ">": operator.gt, "<": operator.lt,
           ">=": operator.ge, "<=": operator.le}

UNION_VALUES = "common/script_values/te_monetary_union_script_values.txt"
UNION_TRIGGERS = "common/scripted_triggers/te_monetary_union_triggers.txt"
UNION_EFFECTS = "common/scripted_effects/te_monetary_union_effects.txt"
PRINCIPLES = "common/power_bloc_principles/extra_power_bloc_principles.txt"
MODIFIERS = "common/static_modifiers/extra_modifiers.txt"
LOC = ROOT / "localization" / "english"


def parse_body(source):
    """An order-preserving parse: a list of (key, operator, value-or-list)."""
    tokens = ParadoxFileParser().tokenize(source)
    pos = 0

    def body():
        nonlocal pos
        result = []
        while pos < len(tokens):
            key = tokens[pos]
            pos += 1
            if key == "}":
                return result
            if pos >= len(tokens) or tokens[pos] not in OPERATORS:
                result.append((key, None, None))
                continue
            op, value = tokens[pos], tokens[pos + 1]
            pos += 2
            result.append((key, op, body() if value == "{" else value.strip('"')))
        return result
    return body()


def definitions(path):
    return {key: value for key, _, value in parse_body((ROOT / path).read_text(encoding="utf-8-sig"))}


def field(body, name):
    return next(val for key, _, val in body if key == name)


def substitute(node, params):
    """Fill a scripted effect's $ARG$ slots, as the engine does per call."""
    if isinstance(node, list):
        return [(substitute(k, params), op, substitute(v, params)) for k, op, v in node]
    if isinstance(node, str):
        for name, value in params.items():
            node = node.replace(f"${name}$", value)
    return node


class Country:
    """One country: what the union's script reads of it."""

    def __init__(self, name, gdp, laws=("law_national_bank", "law_fiat_currency", "law_central_bank_independence"),
                 dial=True, **variables):
        self.name = name
        self.gdp = gdp
        self.laws = set(laws)
        self.dial = dial            # te_mon_has_dial, false for everybody under the simplified rule
        self.bloc = None
        self.vars = dict(variables)
        self.mods = {}              # managed modifier name -> multiplier (1 for a flat one)
        self.sums = {}              # modifier:X totals a scenario fixes (the engine's, not ours)
        self.cycle_running = True

    def __repr__(self):
        return self.name


class Bloc:
    def __init__(self, leader, members, tier):
        self.leader = leader
        self.members = [leader, *members]
        self.tier = tier            # 0 = no Monetary Union principle, else 1 to 5
        for c in self.members:
            c.bloc = self


def adopter(name, gdp, leader="leader", **variables):
    """A member that has adopted: kind 2, anchored on the leader."""
    return Country(name, gdp, dial=False, te_mon_anchor_kind=2, te_mon_anchor=leader,
                   te_mon_union_member=1, **variables)


class Script:
    """Runs the union's values, triggers and effects on a small world."""

    def __init__(self, world_gdp_m=None):
        self.values = {}
        for path in ("common/script_values/te_monetary_script_values.txt",
                     "common/script_values/te_monetary_arrangement_script_values.txt", UNION_VALUES):
            self.values.update(definitions(path))
        # The cycle's phase triggers (banking_cycle_is_*), so a value that asked for one would
        # be run for real, not stubbed; then the monetary files, which win a clash of names.
        self.triggers = definitions("common/scripted_triggers/market_triggers.txt")
        self.triggers.update(definitions("common/scripted_triggers/te_monetary_arrangement_triggers.txt"))
        self.triggers.update(definitions(UNION_TRIGGERS))
        self.effects = definitions("common/scripted_effects/te_monetary_fx_effects.txt")
        self.effects.update(definitions(UNION_EFFECTS))
        self.globals = {} if world_gdp_m is None else {"te_mon_world_gdp_m": world_gdp_m}
        self.stub_values = {}       # script values a scenario fixes instead of running
        self.stub_triggers = {}     # likewise triggers
        self.log = []               # debug_log lines, in order
        # The engine's rule: a modifier added or removed in an effect is not seen by the rest of
        # that effect. While a pulse runs, `opening` holds the names each country carried when
        # it began, and te_mon_mod_has answers from it (None: reads are live).
        self.opening = None

    def pulse(self, body, country):
        """Run one pulse's effects on `country`: has-modifier reads see the pulse's opening state."""
        self.opening = {id(country): set(country.mods)}
        try:
            self.execute(body, country, country)
        finally:
            self.opening = None

    # ---------------------------------------------------------------- values
    def number(self, value, scope, root):
        if isinstance(value, list):
            return self.value(value, scope, root)
        if value.startswith("var:"):
            return scope.vars[value[4:]]        # fail on an unguarded read
        if value.startswith("root.var:"):
            return root.vars[value[len("root.var:"):]]
        if value.startswith("global_var:"):
            return self.globals[value[len("global_var:"):]]
        if value.startswith("scope:te_mon_arr_party."):
            return self.number(value.split(".", 1)[1], self.saved["te_mon_arr_party"], root)
        if value == "gdp":
            return scope.gdp
        if value.startswith("modifier:"):
            return scope.sums[value[len("modifier:"):]]      # a scenario states the sum it reads
        if value == "scaled_debt":
            return scope.vars.get("scaled_debt", 0)
        if value in self.stub_values:
            stub = self.stub_values[value]
            return stub(scope) if callable(stub) else stub
        if value in self.values:
            return self.value(self.values[value], scope, root)
        return float(value)

    def value(self, body, scope, root, initial=0):
        n = initial
        matched = False
        for key, _, val in body:
            if key in ("if", "else_if", "else"):
                condition = key == "else" or self.check(field(val, "limit"), scope, root)
                if (key == "if" or not matched) and condition:
                    n = self.value([item for item in val if item[0] != "limit"], scope, root, n)
                    matched = True
                elif key == "if":
                    matched = False
                continue
            x = self.number(val, scope, root)
            n = {"value": lambda: x, "add": lambda: n + x, "subtract": lambda: n - x,
                 "multiply": lambda: n * x, "divide": lambda: n / x,
                 "min": lambda: max(n, x), "max": lambda: min(n, x)}[key]()
        return n

    # -------------------------------------------------------------- triggers
    def check(self, body, scope, root, mode="AND"):
        answers = []
        for key, op, val in body:
            answer = self.test(key, op, val, scope, root)
            answers.append(answer)
            if mode == "AND" and not answer:
                return False
            if mode == "OR" and answer:
                return True
        if mode in ("NOT", "NOR"):
            return not any(answers)
        return any(answers) if mode == "OR" else all(answers)

    def test(self, key, op, val, scope, root):
        yes = val == "yes"
        if key in ("OR", "AND", "NOT"):
            return self.check(val, scope, root, key)
        if key in self.stub_triggers:
            return self.stub_triggers[key](scope) == yes
        if key == "is_power_bloc_leader":
            return (scope.bloc is not None and scope.bloc.leader is scope) == yes
        if key == "is_in_power_bloc":
            return (scope.bloc is not None) == yes
        if key == "power_bloc":
            return scope.bloc is not None and self.check_bloc(val, scope.bloc, root)
        if key == "te_mon_has_dial":
            return scope.dial == yes
        if key == "has_law_or_variant":
            return val.removeprefix("law_type:") in scope.laws
        if key == "has_variable":
            return val in scope.vars
        if key == "has_global_variable":
            return val in self.globals
        if key == "te_banking_cycle_running":
            return scope.cycle_running == yes
        if (key == "root" and op == "?=" and val == "this") or (key == "this" and val == "root"):
            return scope is root
        if key == "te_mon_mod_has":
            if self.opening is not None and id(scope) in self.opening:
                return field(val, "NAME") in self.opening[id(scope)]
            return field(val, "NAME") in scope.mods
        if key in self.triggers:
            return self.check(self.triggers[key], scope, root) == yes
        if key.startswith("var:") and op == "?=":
            return scope.vars.get(key[4:]) == self.number(val, scope, root)
        return COMPARE[op](self.number(key, scope, root), self.number(val, scope, root))

    def check_bloc(self, body, bloc, root):
        """A power bloc's scope: its principles, its leader, its members."""
        for key, _, val in body:
            if key == "OR":
                answer = any(self.check_bloc([item], bloc, root) for item in val)
            elif key == "has_principle":
                answer = val == f"principle:principle_monetary_union_{bloc.tier}"
            elif key == "has_principle_group":
                assert val == "principle_group:principle_group_monetary_union", val
                answer = bloc.tier >= 1
            elif key == "any_power_bloc_member":
                answer = any(self.check(val, member, root) for member in bloc.members)
            elif key == "power_bloc_leader":
                answer = self.check(val, bloc.leader, root)
            else:
                raise AssertionError(f"unsupported in a power bloc's scope: {key}")
            if not answer:
                return False
        return True

    # --------------------------------------------------------------- effects
    def run(self, name, scope, **params):
        self.saved = getattr(self, "saved", {})
        self.execute(substitute(self.effects[name], params), scope, scope)

    def execute(self, body, scope, root):
        matched = False
        for key, _, val in body:
            if key in ("if", "else_if", "else"):
                condition = key == "else" or self.check(field(val, "limit"), scope, root)
                if (key == "if" or not matched) and condition:
                    self.execute([x for x in val if x[0] != "limit"], scope, root)
                    matched = True
                elif key == "if":
                    matched = False
            else:
                self.statement(key, val, scope, root)

    def statement(self, key, val, scope, root):
        """One effect that is not a branch. A subclass teaches it more (test_banking_overdraft_shed.py)."""
        if key == "set_variable":
            scope.vars[field(val, "name")] = self.number(field(val, "value"), scope, root)
        elif key == "change_variable":
            name = field(val, "name")
            scope.vars[name] = self.value([x for x in val if x[0] != "name"], scope, root, scope.vars[name])
        elif key == "root":
            self.execute(val, root, root)
        elif key == "save_scope_as":
            self.saved[val] = scope
        elif key == "remove_variable":
            del scope.vars[val]
        elif key == "set_global_variable":
            self.globals[val] = True
        elif key == "debug_log":
            self.log.append(val)
        elif key == "power_bloc":
            for item, _, inner in val:
                assert item == "every_power_bloc_member", item
                for member in scope.bloc.members:
                    if self.check(field(inner, "limit"), member, root):
                        self.execute([x for x in inner if x[0] != "limit"], member, root)
        elif key == "te_mon_mod_add":
            scope.mods[field(val, "NAME")] = 1
        elif key == "te_mon_mod_add_scaled":
            assert scope is root, "a scaled add reads root.var: the owner must be ROOT"
            scope.mods[field(val, "NAME")] = scope.vars[field(val, "VAR")]
        elif key == "te_mon_mod_remove":
            del scope.mods[field(val, "NAME")]      # removing a missing modifier logs an error
        elif key in self.effects:
            params = {k: v for k, _, v in val} if isinstance(val, list) else {}
            self.execute(substitute(self.effects[key], params), scope, root)
        else:
            raise AssertionError(f"unsupported effect: {key}")


# The owner's 1957 save: Singapore leads a tier-5 union. GDP in pounds.
SGP_GDP = 128_727_424_256
SGP_ADOPTERS_M = 5_525.8        # the adopters' GDP, millions
SGP_ANCHORED_M = 7_627.6        # adopters and treaty peggers
WORLD_M = 164_603.9


def union(tier, *, adopters=(1_000_000_000,), leader_gdp=10_000_000_000, **leader_kw):
    """A leader, its adopters (by GDP) and one holdout, in a bloc at `tier`."""
    leader = Country("leader", leader_gdp, **leader_kw)
    members = [adopter(f"adopter{i}", gdp) for i, gdp in enumerate(adopters)]
    members.append(Country("holdout", 500_000_000))
    Bloc(leader, members, tier)
    leader.vars["te_mon_union_adopters"] = len(adopters)
    leader.vars["te_mon_union_adopter_gdp_m"] = sum(adopters) / 1e6
    return leader


class TierGateTest(unittest.TestCase):
    """EVERY TIER GATE LISTS EVERY HIGHER TIER (§0.11 ruling T1): a gate that stops short
    reads a bloc that upgraded past it as holding nothing, and here that would take the
    leader's benefits away, and exit every adopter, the month the bloc took the next tier."""

    GATES = {"te_mon_bloc_union_tier_1_plus": 1, "te_mon_bloc_union_tier_2_plus": 2,
             "te_mon_bloc_union_tier_3_plus": 3, "te_mon_bloc_union_tier_4_plus": 4,
             "te_mon_bloc_union_tier_5": 5}

    def setUp(self):
        self.s = Script()

    def test_each_gate_holds_at_its_tier_and_every_tier_above(self):
        for tier in range(0, 6):
            leader = union(tier)
            for gate, floor in self.GATES.items():
                with self.subTest(tier=tier, gate=gate):
                    self.assertEqual(self.s.check(self.s.triggers[gate], leader, leader), tier >= floor)

    def test_each_per_tier_figure_is_its_own_tiers_constant(self):
        figures = {"te_mon_union_seigniorage_pct": "te_mon_union_seigniorage_pct_{}",
                   "te_mon_union_issuer_cut_max": "te_mon_union_issuer_cut_max_{}",
                   "te_mon_union_issuer_bank_value": "te_mon_union_issuer_bank_points_{}",
                   "te_mon_union_credit_value": "te_mon_union_credit_points_{}"}
        for name, constant in figures.items():
            previous = 0
            for tier in range(0, 6):
                leader = union(tier)
                got = self.s.number(name, leader, leader)
                with self.subTest(value=name, tier=tier):
                    if tier < 2:
                        self.assertEqual(got, 0)
                    else:
                        self.assertEqual(got, self.s.number(constant.format(tier), leader, leader))
                        self.assertGreaterEqual(got, previous, "a higher tier pays less")
                        self.assertGreater(got, 0)
                previous = got

    def test_a_higher_tier_never_falls_back_to_a_lower_tiers_branch(self):
        # Every tiered value is an if / else_if ladder from tier 5 down. If the top branches were
        # missing, tier 5 would read tier 2's figure and still pass a "greater than zero" test.
        for name in ("te_mon_union_seigniorage_pct", "te_mon_union_issuer_cut_max"):
            tops = [self.s.number(name, union(tier), None) for tier in (2, 3, 4, 5)]
            with self.subTest(value=name):
                self.assertEqual(len(set(tops)), 4, f"{name} repeats a figure across tiers: {tops}")


class IssuerTest(unittest.TestCase):
    """te_mon_union_is_issuer: leader, tier 2 or above, a currency it can lead with, and a
    member that has adopted (owner, 2026-11-14). Each condition is a removal path."""

    def setUp(self):
        self.s = Script()

    def issuer(self, leader):
        return self.s.check(self.s.triggers["te_mon_union_is_issuer"], leader, leader)

    def test_the_leader_of_an_adopted_currency_is_the_issuer(self):
        for tier in (2, 3, 4, 5):
            with self.subTest(tier=tier):
                self.assertTrue(self.issuer(union(tier)))

    def test_no_adopter_no_issuer(self):
        self.assertFalse(self.issuer(union(5, adopters=())))

    def test_tier_one_has_no_currency_to_issue(self):
        self.assertFalse(self.issuer(union(1)))
        self.assertFalse(self.issuer(union(0)))

    def test_a_leader_without_a_dial_issues_nothing(self):
        # Its law changed, it went on a command economy, or the banking rule left Full:
        # te_mon_has_dial is false for everybody under Simplified.
        self.assertFalse(self.issuer(union(5, dial=False)))

    def test_a_leader_on_metal_issues_nothing(self):
        self.assertFalse(self.issuer(union(5, laws=("law_national_bank", "law_gold_standard"))))

    def test_only_the_leader_is_the_issuer(self):
        leader = union(5)
        for member in leader.bloc.members[1:]:
            with self.subTest(member=member):
                self.assertFalse(self.issuer(member))

    def test_the_adopter_test_is_live_not_the_stored_count(self):
        # The leader's discovery counted an adopter a pulse ago; the member has since left.
        leader = union(5)
        gone = leader.bloc.members[1]
        gone.vars["te_mon_anchor_kind"] = 0
        self.assertEqual(leader.vars["te_mon_union_adopters"], 1)
        self.assertFalse(self.issuer(leader))

    def test_adopters_and_the_issuer_use_the_common_currency_and_holdouts_do_not(self):
        leader = union(3)
        uses = {str(c): self.s.check(self.s.triggers["te_mon_uses_common_currency"], c, c)
                for c in leader.bloc.members}
        self.assertEqual(uses, {"leader": True, "adopter0": True, "holdout": False})


class ReachTest(unittest.TestCase):
    """reach = base / (base + 15% of the leader's GDP); seigniorage and the cut are a tier's
    figure times it."""

    def setUp(self):
        self.s = Script(world_gdp_m=WORLD_M)

    def singapore(self, tier=5):
        leader = union(tier, leader_gdp=SGP_GDP, adopters=(SGP_ADOPTERS_M * 1e6,))
        leader.vars["te_mon_anchored_gdp_m"] = SGP_ANCHORED_M
        return leader

    def reach(self, leader):
        return self.s.number("te_mon_union_reach", leader, leader)

    def test_the_formula(self):
        half = self.s.number("te_mon_union_reach_half_share", None, None)
        self.assertEqual(half, 0.15)
        for share in (0.01, 0.06, 0.15, 0.45, 1.0, 5.0):
            leader = union(3, leader_gdp=1e10, adopters=(share * 1e10,))
            with self.subTest(share=share):
                self.assertAlmostEqual(self.reach(leader), share / (share + half), places=9)

    def test_half_at_fifteen_percent_and_three_quarters_at_forty_five(self):
        # The figures concept_banking_currency_reach_desc gives.
        self.assertAlmostEqual(self.reach(union(2, leader_gdp=1e10, adopters=(1.5e9,))), 0.5)
        self.assertAlmostEqual(self.reach(union(2, leader_gdp=1e10, adopters=(4.5e9,))), 0.75)

    def test_every_adopter_adds_and_no_union_reaches_one(self):
        previous = 0
        for adopters in ((1e8,), (1e8, 1e9), (1e8, 1e9, 1e10), (1e8, 1e9, 1e10, 1e12)):
            reach = self.reach(union(4, leader_gdp=1e10, adopters=adopters))
            self.assertGreater(reach, previous)
            self.assertLess(reach, 1)
            previous = reach

    def test_treaty_peggers_count_at_tier_five_only(self):
        # §0.11 ruling T4: the reserve currency's base is everything anchored on the money.
        for tier, base in ((2, SGP_ADOPTERS_M), (3, SGP_ADOPTERS_M), (4, SGP_ADOPTERS_M), (5, SGP_ANCHORED_M)):
            leader = self.singapore(tier)
            with self.subTest(tier=tier):
                self.assertAlmostEqual(self.s.number("te_mon_union_currency_base_m", leader, leader), base)

    def test_a_tier_five_leader_with_only_treaty_peggers_earns_nothing(self):
        # Owner, 2026-11-14: an adopter is needed at tier V as at the others. The base is there
        # (the peggers' GDP), and it pays nothing until a member of the bloc adopts.
        leader = union(5, adopters=())
        leader.vars["te_mon_anchored_gdp_m"] = 800
        self.assertEqual(self.s.number("te_mon_union_currency_base_m", leader, leader), 800)
        self.assertFalse(self.s.check(self.s.triggers["te_mon_union_is_issuer"], leader, leader))
        self.assertEqual(self.reach(leader), 0)
        self.assertEqual(self.s.number("te_mon_union_seigniorage_value", leader, leader), 0)
        self.assertEqual(self.s.number("te_mon_union_issuer_cut_value", leader, leader), 0)
        self.assertEqual(self.s.number("te_mon_union_seigniorage_value", union(4, adopters=()), None), 0)

    def test_the_peggers_count_once_a_member_has_adopted(self):
        # The same leader with one small adopter: the base is everything anchored, peggers included.
        leader = union(5, leader_gdp=1e10, adopters=(1e8,))
        leader.vars["te_mon_anchored_gdp_m"] = 900          # the adopter's 100 and 800 of peggers
        self.assertAlmostEqual(self.reach(leader), 900 / (900 + 1500))
        leader.bloc.tier = 4
        self.assertAlmostEqual(self.reach(leader), 100 / (100 + 1500))

    def test_reach_asks_for_the_issuer_and_nothing_less(self):
        # The live walk of the members, not the stored sums: a stale count pays nobody.
        body = self.s.values["te_mon_union_reach"]
        limit = field(next(val for key, _, val in body if key == "if"), "limit")
        self.assertEqual(limit, [("te_mon_union_is_issuer", "=", "yes"), ("te_mon_union_currency_base_m", ">", "0")])
        leader = union(5, leader_gdp=1e10, adopters=(1e9,))
        leader.vars["te_mon_anchored_gdp_m"] = 2000
        self.assertGreater(self.reach(leader), 0)
        leader.bloc.members[1].vars["te_mon_anchor_kind"] = 0      # it left; the sums are a month old
        self.assertEqual(self.reach(leader), 0)

    def test_singapore_1957(self):
        # The owner's save: 98 pounds a week before (about 163 minted), of a weekly income of 821 million.
        leader = self.singapore()
        reach = SGP_ANCHORED_M / (SGP_ANCHORED_M + 0.15 * SGP_GDP / 1e6)
        self.assertAlmostEqual(self.reach(leader), reach, places=9)
        self.assertAlmostEqual(reach, 0.283, places=3)
        seigniorage = self.s.number("te_mon_union_seigniorage_value", leader, leader)
        self.assertAlmostEqual(seigniorage, SGP_GDP * 0.015 * reach / 52, delta=seigniorage * 1e-4)
        self.assertTrue(10.4e6 < seigniorage < 10.6e6, seigniorage)
        self.assertAlmostEqual(self.s.number("te_mon_union_issuer_cut_value", leader, leader), 1.5 * reach)

    def test_seigniorage_is_the_tiers_share_of_own_gdp_times_reach(self):
        for tier, pct in ((2, 0.5), (3, 0.75), (4, 1.0), (5, 1.5)):
            leader = union(tier, leader_gdp=4e9, adopters=(6e8,))      # reach one half
            with self.subTest(tier=tier):
                weekly = self.s.number("te_mon_union_seigniorage_value", leader, leader)
                self.assertAlmostEqual(weekly * 52, 4e9 * pct / 100 * 0.5, delta=4e9 * 1e-6)
                self.assertAlmostEqual(self.s.number("te_mon_union_issuer_cut_value", leader, leader), pct * 0.5)

    def test_no_union_however_large_pays_more_than_the_tiers_figure(self):
        # The exploit case: a small leader with adopters a thousand times its size.
        leader = union(5, leader_gdp=1e8, adopters=(1e11,))
        weekly = self.s.number("te_mon_union_seigniorage_value", leader, leader)
        self.assertLess(weekly * 52, 1e8 * 0.015)
        self.assertLess(self.s.number("te_mon_union_issuer_cut_value", leader, leader), 1.5)

    def test_reach_is_zero_for_everyone_who_cannot_issue(self):
        pegged = union(5, adopters=())
        pegged.vars["te_mon_anchored_gdp_m"] = 5000
        cases = {"no bloc": Country("alone", 1e9),
                 "tier 1": union(1),
                 "no dial": union(5, dial=False),
                 "on gold": union(5, laws=("law_national_bank", "law_gold_standard")),
                 "no adopter": union(4, adopters=()),
                 "tier 5, peggers and no adopter": pegged,
                 "a member": union(5).bloc.members[1]}
        for label, country in cases.items():
            with self.subTest(case=label):
                self.assertEqual(self.reach(country), 0)
                self.assertEqual(self.s.number("te_mon_union_seigniorage_value", country, country), 0)
                self.assertEqual(self.s.number("te_mon_union_issuer_cut_value", country, country), 0)

    def test_the_rewrite_step_follows_the_figure(self):
        leader = union(5)
        for pts, step in ((0, 25), (1_000, 25), (10_000_000, 100_000)):
            leader.vars["te_mon_union_seigniorage_pts"] = pts
            with self.subTest(pts=pts):
                self.assertEqual(self.s.number("te_mon_union_seigniorage_step", leader, leader), step)
                self.assertEqual(self.s.number("te_mon_union_seigniorage_step_neg", leader, leader), -step)


class CentralBankTest(unittest.TestCase):
    """The issuer's extra interventions, and the one banking law they stop at."""

    def setUp(self):
        self.s = Script()

    def points(self, leader):
        return self.s.number("te_mon_union_issuer_bank_value", leader, leader)

    def test_the_ladder_with_the_banking_unions_point_is_one_two_three_four(self):
        own = [self.points(union(tier)) for tier in (2, 3, 4, 5)]
        self.assertEqual(own, [1, 2, 2, 3])
        union_point = float(definitions(MODIFIERS)["te_mon_union_banking_union"][-1][2])
        self.assertEqual(definitions(MODIFIERS)["te_mon_union_banking_union"][-1][0], "country_banking_intervention_max_add")
        totals = [p + (union_point if tier >= 4 else 0) for tier, p in zip((2, 3, 4, 5), own)]
        self.assertEqual(totals, [1, 2, 3, 4])

    def test_unregulated_banking_gets_no_points(self):
        # Its budget is its identity: 2 with the national bank, and its unlocked tools cost 3 and 4.
        laws = ("law_national_bank", "law_fiat_currency", "law_unregulated_banking")
        for tier in (2, 3, 4, 5):
            with self.subTest(tier=tier):
                self.assertEqual(self.points(union(tier, laws=laws)), 0)

    def test_every_other_banking_law_gets_them(self):
        for law in ("law_free_mutual_banking", "law_universal_banking_light_prudence",
                    "law_prudential_narrow_banking", "law_directed_credit_development_banks",
                    "law_central_bank_independence"):
            with self.subTest(law=law):
                self.assertEqual(self.points(union(5, laws=("law_national_bank", "law_fiat_currency", law))), 3)

    def test_no_issuer_no_points(self):
        self.assertEqual(self.points(union(5, adopters=())), 0)
        self.assertEqual(self.points(union(5, dial=False)), 0)
        self.assertEqual(self.points(union(1)), 0)

    def test_the_budget_total_counts_the_issuers_points(self):
        text = (ROOT / "common/script_values/extra_script_values.txt").read_text(encoding="utf-8-sig")
        total = text[text.index("banking_display_points_total = {"):]
        total = total[:total.index("\n}\n")]
        self.assertIn("te_mon_mod_has = { NAME = te_mon_union_issuer_bank } } add = var:te_mon_union_issuer_bank_applied",
                      total)


class CapitalMarketTest(unittest.TestCase):
    """te_mon_union_credit_value: adopters and the issuer, by tier, the same in every phase of
    the cycle, and nothing where the pool cannot be spent."""

    # One cycle value in each phase (market_triggers.txt: 10 / 25 / 40 / 60 / 75 / 88).
    PHASES = {"panic": 5, "downturn": 15, "stagnation": 30, "stable": 50, "expansion": 65, "boom": 80,
              "frenzy": 95}

    def setUp(self):
        self.s = Script()

    def credit(self, country):
        return self.s.number("te_mon_union_credit_value", country, country)

    def test_by_tier_for_the_issuer_and_for_an_adopter(self):
        for tier, points in ((2, 2), (3, 2), (4, 3), (5, 5)):
            leader = union(tier)
            with self.subTest(tier=tier):
                self.assertEqual(self.credit(leader), points)
                self.assertEqual(self.credit(leader.bloc.members[1]), points)

    def test_a_holdout_and_a_leader_nobody_has_joined_get_none(self):
        leader = union(5)
        self.assertEqual(self.credit(leader.bloc.members[-1]), 0)
        self.assertEqual(self.credit(union(5, adopters=())), 0)

    def test_the_phases_are_the_cycles_own(self):
        # The grid below means nothing unless each cycle value lands in the phase it is named for.
        country = Country("c", 1e9)
        for phase, value in self.PHASES.items():
            country.vars["finance_cycle_value"] = value
            holds = [name for name in self.PHASES
                     if self.s.check(self.s.triggers[f"banking_cycle_is_{name}"], country, country)]
            with self.subTest(phase=phase):
                self.assertEqual(holds, [phase])
        country.vars["finance_cycle_value"] = self.PHASES["downturn"]
        self.assertTrue(self.s.check(self.s.triggers["banking_cycle_is_recession"], country, country))

    def test_the_same_in_every_phase_of_the_cycle(self):
        # Owner, 2026-11-14: "The investment pool contribution decrease is the worst part of
        # downturns and panics. I worry this would make them less painful." As first built the
        # bonus doubled in a downturn or panic; it is flat now, and this holds it there.
        for tier, points in ((2, 2), (3, 2), (4, 3), (5, 5)):
            for phase, value in self.PHASES.items():
                for momentum, bubble in ((-5, 0), (0, 40), (5, 95)):
                    for running in (True, False):
                        leader = union(tier)
                        member = leader.bloc.members[1]
                        for country in (leader, member):
                            country.cycle_running = running
                            country.vars.update(finance_cycle_value=value, finance_cycle_momentum=momentum,
                                                bubble_pressure=bubble)
                        with self.subTest(tier=tier, phase=phase, momentum=momentum, bubble=bubble,
                                          running=running):
                            self.assertEqual(self.credit(leader), points)
                            self.assertEqual(self.credit(member), points)

    def test_a_slump_keeps_its_whole_drop_in_the_pool(self):
        # The downturn's and the panic's own cut to capitalists' contribution stands in full
        # against the good times: the bonus is the same on both sides of the comparison.
        unit = float(dict((k, v) for k, _, v in definitions(MODIFIERS)["te_mon_union_credit"])
                     ["state_capitalists_investment_pool_contribution_add"])
        key = "state_capitalists_investment_pool_contribution_add"
        for phase in ("downturn", "panic"):
            cut = float(dict((k, v) for k, _, v in definitions(MODIFIERS)[f"financial_cycle_phase_{phase}"])[key])
            self.assertLess(cut, 0)
            for tier in (2, 3, 4, 5):
                leader = union(tier)
                leader.vars["finance_cycle_value"] = self.PHASES["stable"]
                good = self.credit(leader) * unit
                leader.vars["finance_cycle_value"] = self.PHASES[phase]
                bad = self.credit(leader) * unit + cut
                with self.subTest(phase=phase, tier=tier):
                    self.assertAlmostEqual(bad - good, cut)

    def test_nothing_the_leader_is_paid_reads_the_cycle(self):
        # Not the capital market, and not reach, the seigniorage, the cut or the points either:
        # none of them may come to depend on the phase, the momentum or the bubble.
        cycle_words = ("cycle", "recession", "panic", "downturn", "stagnation", "slump", "bubble", "momentum",
                       "frenzy", "boom")

        def words(node):
            if isinstance(node, list):
                for key, _, val in node:
                    yield key
                    yield from words(val)
            elif isinstance(node, str):
                yield node

        seen, queue = set(), ["te_mon_union_credit_value", "te_mon_union_reach", "te_mon_union_seigniorage_value",
                              "te_mon_union_issuer_cut_value", "te_mon_union_issuer_bank_value"]
        while queue:
            name = queue.pop()
            if name in seen:
                continue
            seen.add(name)
            body = self.s.values.get(name) or self.s.triggers.get(name)
            for word in words(body):
                with self.subTest(value=name, token=word):
                    self.assertFalse(any(w in word for w in cycle_words), f"{name} reads the cycle: {word}")
                if word in self.s.values or (word.startswith("te_mon_") and word in self.s.triggers):
                    queue.append(word)
        self.assertGreater(len(seen), 20, "the walk did not follow the values' references")
        for name in ("te_mon_union_credit", "te_mon_union_issuer_premium", "te_mon_union_issuer_bank",
                     "te_mon_union_seigniorage"):
            fields = [k for k, _, _ in definitions(MODIFIERS)[name]]
            self.assertFalse([f for f in fields if any(w in f for w in ("crash", "momentum", "bubble", "finance_"))],
                             f"{name} carries a line that acts on the cycle")

    def test_none_where_the_pool_cannot_be_spent(self):
        # Excess Private Construction: more deposits would deepen its construction penalty.
        leader = union(5)
        leader.vars["too_much_private_construction_cached"] = 340.5
        self.assertEqual(self.credit(leader), 0)
        leader.vars["too_much_private_construction_cached"] = 0
        self.assertEqual(self.credit(leader), 5)


class StepNineBTest(unittest.TestCase):
    """te_monetary_update_union, from the write of te_mon_union_q_state on: the managed
    modifiers go on, follow the tier, and come off the pulse the condition fails."""

    ISSUER_ONLY = ("te_mon_union_seigniorage", "te_mon_union_issuer_premium", "te_mon_union_issuer_bank")
    SHARED = ("te_mon_union_adopter", "te_mon_union_banking_union", "te_mon_union_reserve", "te_mon_union_credit")

    def setUp(self):
        self.s = Script(world_gdp_m=WORLD_M)
        body = self.s.effects["te_monetary_update_union"]
        after = next(i for i, (key, _, val) in enumerate(body)
                     if key == "set_variable" and field(val, "name") == "te_mon_union_q_state")
        # te_monetary_apply_fx_one uses te_mon_work, the scratch the Question's signature is built
        # in: nothing that calls it may come before the signature is stored.
        before = repr(body[:after])
        for name in ("te_monetary_apply_fx_one", "te_mon_mod_add", "te_mon_mod_remove"):
            self.assertNotIn(name, before, f"{name} runs before te_mon_union_q_state is written")
        self.tail = body[after + 1:]

    def seed(self, country):
        self.s.run("te_monetary_init_union_variables", country)
        country.vars.setdefault("te_mon_work", 0)
        country.vars.setdefault("te_mon_work2", 0)

    def pulse(self, country):
        self.seed(country)
        self.s.pulse(self.tail, country)

    def discover(self, leader):
        """The leader's discovery: only the sums this change added are run for real."""
        self.s.stub_values.update(te_mon_union_cost_to_root=0, te_mon_union_adopt_score=1)
        self.s.stub_triggers["te_mon_union_is_holdout"] = lambda scope: False
        for name in ("te_mon_arr_provider_pts", "te_mon_bs_union_pts"):
            leader.vars.setdefault(name, 0)
        self.seed(leader)
        self.s.run("te_monetary_discover_union", leader)

    def test_the_discovery_counts_adopters_and_sums_their_gdp(self):
        leader = union(3, adopters=(2e9, 5e8, 1e7))
        leader.vars.update(te_mon_union_adopters=99, te_mon_union_adopter_gdp_m=99)
        self.discover(leader)
        self.assertEqual(leader.vars["te_mon_union_adopters"], 3)
        self.assertAlmostEqual(leader.vars["te_mon_union_adopter_gdp_m"], 2510)

    def test_the_discovery_zeroes_the_sums_of_a_country_that_no_longer_leads(self):
        leader = union(3)
        leader.vars.update(te_mon_union_adopters=4, te_mon_union_adopter_gdp_m=900)
        leader.bloc.leader = leader.bloc.members[1]
        self.discover(leader)
        self.assertEqual(leader.vars["te_mon_union_adopters"], 0)
        self.assertEqual(leader.vars["te_mon_union_adopter_gdp_m"], 0)

    def test_a_tier_five_issuer_carries_everything(self):
        leader = union(5, leader_gdp=SGP_GDP, adopters=(SGP_ADOPTERS_M * 1e6,))
        leader.vars["te_mon_anchored_gdp_m"] = SGP_ANCHORED_M
        self.pulse(leader)
        self.assertEqual(set(leader.mods), set(self.ISSUER_ONLY + self.SHARED))
        self.assertEqual(leader.mods["te_mon_union_issuer_bank"], 3)
        self.assertEqual(leader.mods["te_mon_union_credit"], 5)
        self.assertAlmostEqual(leader.mods["te_mon_union_issuer_premium"], 0.4248, places=3)
        self.assertTrue(10.4e6 < leader.mods["te_mon_union_seigniorage"] < 10.6e6)
        # The trackers the next pulse compares against: each modifier's own.
        self.assertEqual(leader.vars["te_mon_union_issuer_bank_applied"], 3)
        self.assertEqual(leader.vars["te_mon_union_credit_applied"], 5)
        self.assertEqual(leader.vars["te_mon_union_seigniorage_applied"], leader.mods["te_mon_union_seigniorage"])
        self.assertEqual(leader.vars["te_mon_union_issuer_cut_applied"], leader.mods["te_mon_union_issuer_premium"])
        self.assertEqual(leader.vars["te_mon_union_pressure_applied"], 0)

    # What one unit of each scaled modifier is. The multiplier is the script value, so the unit
    # is half of every figure: 10 for 1 here mints ten times the seigniorage, and a flipped
    # sign turns the cut into a surcharge, with every value and tracker reading as before.
    UNITS = {"te_mon_union_seigniorage": ("country_minting_add", "1"),
             "te_mon_union_issuer_premium": ("country_risk_premium_add", "-0.01"),
             "te_mon_union_issuer_bank": ("country_banking_intervention_max_add", "1"),
             "te_mon_union_credit": ("state_capitalists_investment_pool_contribution_add", "0.01"),
             "te_mon_union_pressure": ("country_influence_cost_add", "50")}

    def test_one_unit_of_each_scaled_modifier(self):
        static = definitions(MODIFIERS)
        for name, (key, unit) in self.UNITS.items():
            with self.subTest(modifier=name):
                effects = [(k, v) for k, _, v in static[name] if k != "icon"]
                self.assertEqual(effects, [(key, unit)])

    # The modifier each call steps, what it reads and where it remembers what it applied.
    TRACKERS = {"te_mon_union_seigniorage": ("var:te_mon_union_seigniorage_pts", "te_mon_union_seigniorage_applied"),
                "te_mon_union_issuer_premium": ("var:te_mon_union_issuer_cut_pts", "te_mon_union_issuer_cut_applied"),
                "te_mon_union_issuer_bank": ("var:te_mon_union_issuer_bank_pts", "te_mon_union_issuer_bank_applied"),
                "te_mon_union_credit": ("var:te_mon_union_credit_pts", "te_mon_union_credit_applied"),
                "te_mon_union_pressure": ("var:te_mon_work", "te_mon_union_pressure_applied")}

    def test_each_scaled_modifier_has_its_own_tracker(self):
        calls = {}

        def collect(body):
            for key, _, val in body:
                if key == "te_monetary_apply_fx_one":
                    args = dict((k, v) for k, _, v in val)
                    self.assertNotIn(args["NAME"], calls, "a modifier is stepped twice in one pulse")
                    calls[args["NAME"]] = (args["VALUE"], args["APPLIED"])
                elif isinstance(val, list):
                    collect(val)
        collect(self.s.effects["te_monetary_update_union"])
        self.assertEqual(calls, self.TRACKERS)
        self.assertEqual(set(calls), set(self.UNITS))

    def test_no_two_scaled_modifiers_anywhere_share_a_tracker(self):
        # A shared tracker makes each call see the other's figure as its own last write: both
        # modifiers are rewritten every pulse, and the one that comes off zeroes the other's.
        seen = {}
        for path in sorted((ROOT / "common/scripted_effects").glob("*.txt")):
            text = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))
            for call in re.findall(r"te_monetary_apply_fx_one = \{([^{}]*)\}", text):
                args = dict(re.findall(r"(\w+) = (\S+)", call))
                if "$" in args["NAME"] or "$" in args["APPLIED"]:
                    continue
                self.assertEqual(seen.setdefault(args["APPLIED"], args["NAME"]), args["NAME"],
                                 f"{args['APPLIED']} is the tracker of two modifiers")
        self.assertGreater(len(seen), 8)
        self.assertEqual(len(set(seen.values())), len(seen), "a modifier with two trackers")

    def test_what_each_tier_puts_on_the_issuer(self):
        expected = {2: {"te_mon_union_adopter"}, 3: {"te_mon_union_adopter"},
                    4: {"te_mon_union_adopter", "te_mon_union_banking_union"},
                    5: {"te_mon_union_adopter", "te_mon_union_banking_union", "te_mon_union_reserve"}}
        for tier, shared in expected.items():
            leader = union(tier)
            self.pulse(leader)
            with self.subTest(tier=tier):
                self.assertEqual(set(leader.mods) - set(self.ISSUER_ONLY) - {"te_mon_union_credit"}, shared)
                self.assertTrue(set(self.ISSUER_ONLY) <= set(leader.mods))

    def test_an_adopter_carries_the_shared_ones_and_none_of_the_issuers(self):
        leader = union(5)
        member = leader.bloc.members[1]
        self.pulse(member)
        self.assertEqual(set(member.mods), set(self.SHARED))

    def test_a_holdout_carries_nothing(self):
        leader = union(5)
        holdout = leader.bloc.members[-1]
        self.pulse(holdout)
        self.assertEqual(holdout.mods, {})

    def test_an_unregulated_issuer_gets_neither_the_points_nor_the_banking_union(self):
        laws = ("law_national_bank", "law_fiat_currency", "law_unregulated_banking")
        leader = union(5, laws=laws)
        self.pulse(leader)
        self.assertNotIn("te_mon_union_issuer_bank", leader.mods)
        self.assertNotIn("te_mon_union_banking_union", leader.mods)
        # The rest of the currency's gains do not hang on the banking law.
        for name in ("te_mon_union_adopter", "te_mon_union_reserve", "te_mon_union_seigniorage",
                     "te_mon_union_issuer_premium", "te_mon_union_credit"):
            self.assertIn(name, leader.mods)
        # An adopter under the same law is outside the banking union too (#1812): until 2026-11-15
        # it kept the modifier, and with it a third point on a budget whose limit is its law.
        member = leader.bloc.members[1]
        member.laws = set(laws)
        self.pulse(member)
        self.assertNotIn("te_mon_union_banking_union", member.mods)
        self.assertEqual(member.vars["te_mon_union_banking_applied"], 0)
        for name in ("te_mon_union_adopter", "te_mon_union_reserve", "te_mon_union_credit"):
            self.assertIn(name, member.mods)

    def removal(self, change):
        leader = union(5)
        leader.vars["te_mon_anchored_gdp_m"] = 1000
        self.pulse(leader)
        self.assertEqual(set(leader.mods), set(self.ISSUER_ONLY + self.SHARED))
        change(leader)
        # The discovery runs first in a pulse (step 1c) and re-derives the sums.
        self.discover(leader)
        self.pulse(leader)
        return leader

    def test_losing_the_dial_takes_everything_off_the_same_pulse(self):
        def lose_dial(leader):
            leader.dial = False
            # ...and the adopters exit with it: no common currency left to be in.
            for member in leader.bloc.members[1:]:
                member.vars["te_mon_anchor_kind"] = 0
        self.assertEqual(self.removal(lose_dial).mods, {})

    def test_the_last_adopter_leaving_takes_everything_off(self):
        # At tier V, and with a treaty pegger still anchored on the leader's money: the base
        # stays above zero, and seigniorage and the cut go all the same (owner, 2026-11-14).
        def exit_all(leader):
            for member in leader.bloc.members[1:]:
                member.vars["te_mon_anchor_kind"] = 0
            leader.vars["te_mon_anchored_gdp_m"] = 800
        leader = self.removal(exit_all)
        self.assertEqual(leader.bloc.tier, 5)
        self.assertEqual(self.s.number("te_mon_union_currency_base_m", leader, leader), 800)
        self.assertEqual(leader.mods, {})
        for name in ("te_mon_union_seigniorage_applied", "te_mon_union_issuer_cut_applied"):
            self.assertEqual(leader.vars[name], 0)

    def test_no_longer_leading_takes_everything_off(self):
        def deposed(leader):
            leader.bloc.leader = leader.bloc.members[2]
        self.assertEqual(self.removal(deposed).mods, {})

    def test_a_tier_drop_steps_every_figure_down_and_exits_nobody(self):
        def drop(leader):
            leader.bloc.tier = 4
        leader = self.removal(drop)
        self.assertNotIn("te_mon_union_reserve", leader.mods)
        self.assertEqual(leader.mods["te_mon_union_issuer_bank"], 2)
        self.assertEqual(leader.mods["te_mon_union_credit"], 3)
        self.assertIn("te_mon_union_banking_union", leader.mods)
        self.assertTrue(self.s.check(self.s.triggers["te_mon_union_is_issuer"], leader, leader))

    def test_a_drop_to_tier_one_takes_everything_off(self):
        def drop(leader):
            leader.bloc.tier = 1
            for member in leader.bloc.members[1:]:
                member.vars["te_mon_anchor_kind"] = 0
        self.assertEqual(self.removal(drop).mods, {})

    def test_enacting_unregulated_banking_takes_the_points_and_the_banking_union(self):
        def deregulate(leader):
            leader.laws = {"law_national_bank", "law_fiat_currency", "law_unregulated_banking"}
        leader = self.removal(deregulate)
        self.assertNotIn("te_mon_union_issuer_bank", leader.mods)
        self.assertNotIn("te_mon_union_banking_union", leader.mods)
        self.assertEqual(leader.vars["te_mon_union_issuer_bank_applied"], 0)

    def test_a_missing_modifier_is_put_back(self):
        # A revolution's winner inherits the trackers and no modifiers; a change of the
        # modifiers' home strips them. Either way the next pulse finds them gone.
        leader = union(5)
        leader.vars["te_mon_anchored_gdp_m"] = 1000
        self.pulse(leader)
        before = dict(leader.mods)
        leader.mods.clear()
        self.pulse(leader)
        self.assertEqual(leader.mods, before)

    def test_every_new_managed_modifier_is_in_the_strip_list(self):
        text = re.sub(r"#[^\n]*", "", (ROOT / "common/scripted_effects/te_monetary_effects.txt")
                      .read_text(encoding="utf-8-sig"))
        for name in ("te_mon_union_issuer_premium", "te_mon_union_issuer_bank", "te_mon_union_credit"):
            self.assertIn(f"te_mon_mod_strip = {{ NAME = {name} }}", text)


UNREGULATED = ("law_national_bank", "law_fiat_currency", "law_unregulated_banking")
REGULATED = ("law_free_mutual_banking", "law_universal_banking_light_prudence", "law_prudential_narrow_banking",
             "law_directed_credit_development_banks", "law_central_bank_independence")
POINTS = "country_banking_intervention_max_add"


class ScoreScript(Script):
    """The adoption score reads three things the union's own tests never needed. Each is a fact
    of the scenario here, the same for both countries compared, so only the law differs."""

    def test(self, key, op, val, scope, root):
        if key == "exists":
            return False                    # no market owner to share: the +30 is out for both
        if key == "country_rank":
            return False                    # neither is a great power
        return super().test(key, op, val, scope, root)


class RegulatorTest(unittest.TestCase):
    """Unregulated Banking's budget is its lock (banking_possible_cb_bail_in_regime: "no law lock:
    the budget is below the cost already"), so nothing may add a point under that law. PR #1810
    asked that of the issuer only; an adopter kept the banking union and its point, 3 with its
    national bank, which is the Bail-in Regime's cost (#1812: 9 of 57 adopters in the owner's
    1958 save were under that law, and the four whose banking entries were read carried it)."""

    def setUp(self):
        self.s = Script(world_gdp_m=WORLD_M)
        body = self.s.effects["te_monetary_update_union"]
        after = next(i for i, (key, _, val) in enumerate(body)
                     if key == "set_variable" and field(val, "name") == "te_mon_union_q_state")
        self.tail = body[after + 1:]

    def pulse(self, country):
        self.s.run("te_monetary_init_union_variables", country)
        country.vars.setdefault("te_mon_work", 0)
        country.vars.setdefault("te_mon_work2", 0)
        self.s.pulse(self.tail, country)

    def adopter_under(self, tier, law):
        leader = union(tier)
        member = leader.bloc.members[1]
        member.laws = {"law_national_bank", "law_fiat_currency", law}
        return member

    def test_an_adopter_under_unregulated_banking_is_outside_the_banking_union(self):
        for tier in (4, 5):
            member = self.adopter_under(tier, "law_unregulated_banking")
            self.pulse(member)
            with self.subTest(tier=tier):
                self.assertNotIn("te_mon_union_banking_union", member.mods)
                self.assertTrue(self.s.check(self.s.triggers["te_mon_union_outside_banking_union"], member, member))
                self.assertFalse(self.s.check(self.s.triggers["te_mon_union_in_banking_union"], member, member))

    def test_an_adopter_under_every_other_banking_law_is_in_it(self):
        for law in REGULATED:
            member = self.adopter_under(4, law)
            self.pulse(member)
            with self.subTest(law=law):
                self.assertEqual(member.mods.get("te_mon_union_banking_union"), 1)
                self.assertFalse(self.s.check(self.s.triggers["te_mon_union_outside_banking_union"], member, member))

    def test_below_tier_four_nobody_is_in_it_and_nobody_is_told_they_are_out(self):
        for tier in (2, 3):
            for law in ("law_unregulated_banking", "law_central_bank_independence"):
                member = self.adopter_under(tier, law)
                self.pulse(member)
                with self.subTest(tier=tier, law=law):
                    self.assertNotIn("te_mon_union_banking_union", member.mods)
                    self.assertFalse(self.s.check(self.s.triggers["te_mon_union_outside_banking_union"], member, member))

    def test_a_holdout_is_neither_in_nor_told_it_is_out(self):
        holdout = union(5).bloc.members[-1]
        holdout.laws = set(UNREGULATED)
        for name in ("te_mon_union_in_banking_union", "te_mon_union_outside_banking_union"):
            self.assertFalse(self.s.check(self.s.triggers[name], holdout, holdout), name)

    def test_enacting_unregulated_banking_takes_it_off_an_adopter_on_its_next_pulse(self):
        member = self.adopter_under(4, "law_universal_banking_light_prudence")
        self.pulse(member)
        self.assertIn("te_mon_union_banking_union", member.mods)
        member.laws = set(UNREGULATED)
        self.pulse(member)
        self.assertNotIn("te_mon_union_banking_union", member.mods)
        self.assertEqual(member.vars["te_mon_union_banking_applied"], 0)
        # ...and a regulated law puts it back.
        member.laws = {"law_national_bank", "law_fiat_currency", "law_free_mutual_banking"}
        self.pulse(member)
        self.assertIn("te_mon_union_banking_union", member.mods)

    def grants(self):
        """{static modifier: points} for every modifier in the mod that ADDS intervention points."""
        return {name: float(v) for name, body in definitions(MODIFIERS).items() if isinstance(body, list)
                for k, _, v in body if k == POINTS and float(v) > 0}

    def test_every_grant_of_points_from_a_modifier_asks_for_a_regulator(self):
        # The two the Monetary Union pays. A third grant added without the test would reopen #1812.
        self.assertEqual(set(self.grants()), {"te_mon_union_banking_union", "te_mon_union_issuer_bank"})
        for tier in (2, 3, 4, 5):
            for who in ("issuer", "adopter"):
                leader = union(tier, laws=UNREGULATED)
                country = leader if who == "issuer" else leader.bloc.members[1]
                country.laws = set(UNREGULATED)
                self.pulse(country)
                with self.subTest(tier=tier, who=who):
                    self.assertEqual([m for m in country.mods if m in self.grants()], [])

    def test_the_budget_under_unregulated_banking_stays_below_the_bail_ins_cost(self):
        # The comment over banking_possible_cb_bail_in_regime, as arithmetic from the files it names.
        laws = definitions("common/laws/extra_laws.txt")

        def law_points(name):
            return sum(float(v) for key, _, block in laws[name] if key == "modifier"
                       for k, _, v in block if k == POINTS)

        budget = law_points("law_unregulated_banking") + law_points("law_national_bank")
        self.assertEqual(budget, 2)
        bail_in = definitions("common/scripted_triggers/banking_policy_triggers.txt")["banking_possible_cb_bail_in_regime"]
        cost = next(float(v) for key, _, block in bail_in if key == "custom_tooltip"
                    for k, op, v in block if k == f"modifier:{POINTS}" and op == ">=")
        self.assertEqual(cost, 3)
        self.assertLess(budget, cost)
        # What reopened it: one grant on top is the cost exactly.
        self.assertEqual(budget + self.grants()["te_mon_union_banking_union"], cost)

    def test_the_adoption_score_counts_the_supervisor_only_where_there_is_a_regulator(self):
        s = ScoreScript()
        s.stub_values["te_mon_credibility_c_own"] = 0.5
        s.stub_triggers["te_mon_union_leader_is_pressing"] = lambda scope: False

        def score(tier, law):
            holdout = union(tier).bloc.members[-1]
            holdout.laws = {"law_national_bank", "law_fiat_currency", law}
            return s.number("te_mon_union_adopt_score", holdout, holdout)

        for tier, gap in ((2, 0), (3, 0), (4, 5), (5, 5)):
            with self.subTest(tier=tier):
                self.assertEqual(score(tier, "law_universal_banking_light_prudence")
                                 - score(tier, "law_unregulated_banking"), gap)

    def test_the_monetary_union_row_says_why(self):
        loc = english()
        self.assertIn("[Country.GetCustom('te_mon_union_regulator_note')]", loc["banking_dash_mon_union_tt"])
        note = loc["banking_dash_mon_union_regulator_note"]
        self.assertIn("$law_unregulated_banking$", note)
        self.assertIn("intervention point", note)
        self.assertEqual(loc["banking_dash_mon_union_regulator_note_none"], "")
        block = definitions("common/customizable_localization/banking_dash_custom_loc.txt")["te_mon_union_regulator_note"]
        texts = [val for key, _, val in block if key == "text"]
        self.assertEqual([field(t, "localization_key") for t in texts],
                         ["banking_dash_mon_union_regulator_note", "banking_dash_mon_union_regulator_note_none"])
        self.assertEqual(field(texts[0], "trigger"), [("te_mon_union_outside_banking_union", "=", "yes")])

    def test_the_principles_lines_name_the_law_for_both_sides(self):
        loc = english()
        for key in ("power_bloc_banking_union_bool_desc", "power_bloc_te_mon_currency_crash_chance_mult_desc",
                    "power_bloc_te_mon_currency_volatility_mult_desc", "power_bloc_te_mon_currency_interventions_add_desc"):
            with self.subTest(key=key):
                self.assertIn("$law_unregulated_banking$", loc[key])
                # The old wording gave the exception to the leader alone.
                self.assertNotIn("every adopter, and", loc[key])
                self.assertNotIn("the leader under any banking law", loc[key])

    def test_one_trigger_gates_both_sides(self):
        text = re.sub(r"#[^\n]*", "", (ROOT / UNION_EFFECTS).read_text(encoding="utf-8-sig"))
        self.assertEqual(text.count("te_mon_union_in_banking_union = yes"), 1)
        for path in (UNION_EFFECTS, UNION_VALUES, UNION_TRIGGERS):
            code = re.sub(r"#[^\n]*", "", (ROOT / path).read_text(encoding="utf-8-sig"))
            self.assertNotIn("te_mon_union_issuer_has_regulator", code, path)
        comment = (ROOT / "common/scripted_triggers/banking_policy_triggers.txt").read_text(encoding="utf-8-sig")
        self.assertIn("THE BUDGET IS THE LOCK", comment)


class SelfCheckTest(unittest.TestCase):
    """TE_SELF_CHECK mon_union_issuer: one line a game, read on the second pulse a leader
    with a real adopter qualifies, and never OK on a union with nothing to check."""

    def setUp(self):
        self.s = Script(world_gdp_m=WORLD_M)
        body = self.s.effects["te_monetary_update_union"]
        after = next(i for i, (key, _, val) in enumerate(body)
                     if key == "set_variable" and field(val, "name") == "te_mon_union_q_state")
        self.tail = body[after + 1:]
        self.assertEqual(self.tail[-1][0], "te_mon_selfcheck_union_issuer")

    def pulse(self, leader):
        self.s.run("te_monetary_init_union_variables", leader)
        for name in ("te_mon_work", "te_mon_work2"):
            leader.vars.setdefault(name, 0)
        leader.vars["te_mon_work_gdp"] = leader.gdp      # the discovery caches it
        self.s.pulse(self.tail, leader)

    def test_ok_on_the_second_pulse_and_once_a_game(self):
        leader = union(5, adopters=(2e9,))
        self.pulse(leader)
        self.assertEqual(self.s.log, [], "the first pulse only marks the leader: its adds are not visible yet")
        self.assertIn("te_mon_union_issuer_check", leader.vars)
        self.pulse(leader)
        self.assertEqual(len(self.s.log), 1)
        self.assertTrue(self.s.log[0].startswith("TE_SELF_CHECK OK mon_union_issuer "), self.s.log[0])
        self.assertNotIn("te_mon_union_issuer_check", leader.vars)
        for _ in range(3):
            self.pulse(leader)
        self.assertEqual(len(self.s.log), 1)

    def leave(self, leader):
        """The one adopter goes back to its own money; the discovery re-derives the sums."""
        leader.bloc.members[1].vars["te_mon_anchor_kind"] = 0
        leader.vars.update(te_mon_union_adopters=0, te_mon_union_adopter_gdp_m=0)

    def rejoin(self, leader, gdp):
        leader.bloc.members[1].vars["te_mon_anchor_kind"] = 2
        leader.vars.update(te_mon_union_adopters=1, te_mon_union_adopter_gdp_m=gdp / 1e6)

    def test_a_leader_that_stops_qualifying_starts_again_from_its_first_pulse(self):
        # Review of PR #1810, finding E. Marked on its first pulse, then the adopter leaves and
        # everything comes off. When a member adopts again, that pulse puts the modifiers back,
        # and they are not visible to it: read as the second pulse it logged a false BROKEN.
        leader = union(5, adopters=(2e9,))
        self.pulse(leader)
        self.assertIn("te_mon_union_issuer_check", leader.vars)
        self.leave(leader)
        self.pulse(leader)
        self.assertEqual(leader.mods, {})
        self.assertNotIn("te_mon_union_issuer_check", leader.vars, "the mark goes when the leader stops qualifying")
        self.assertEqual(self.s.log, [])
        self.rejoin(leader, 2e9)
        self.pulse(leader)
        self.assertEqual(self.s.log, [], "a first pulse again: its own adds are not visible to it")
        self.assertIn("te_mon_union_issuer_check", leader.vars)
        self.pulse(leader)
        self.assertEqual(len(self.s.log), 1)
        self.assertTrue(self.s.log[0].startswith("TE_SELF_CHECK OK mon_union_issuer "), self.s.log[0])

    def test_a_mark_left_behind_is_cleared_once_another_leader_has_logged(self):
        # The line is once a game: a second leader marked in the same month must not keep its mark.
        leader = union(5, adopters=(2e9,))
        self.pulse(leader)
        self.s.globals["te_mon_union_issuer_selfcheck_logged"] = True
        self.pulse(leader)
        self.assertNotIn("te_mon_union_issuer_check", leader.vars)
        self.assertEqual(self.s.log, [])

    def test_ok_at_the_edge_of_the_gate(self):
        # The smallest union the check reads: tier II, one adopter at exactly 1% of the leader's
        # GDP. Reach 0.0625, a cut of 0.031 points: under the 0.05 step, and still written, because
        # a modifier that is missing is always put on.
        leader = union(2, leader_gdp=1e10, adopters=(1e8,))
        self.pulse(leader)
        self.assertAlmostEqual(leader.mods["te_mon_union_issuer_premium"], 0.03125)
        self.pulse(leader)
        self.assertTrue(self.s.log and self.s.log[0].startswith("TE_SELF_CHECK OK mon_union_issuer "), self.s.log)

    def test_broken_when_the_discovery_summed_nothing(self):
        leader = union(5, adopters=(2e9,))
        leader.vars.update(te_mon_union_adopters=0, te_mon_union_adopter_gdp_m=0)
        self.pulse(leader)
        self.pulse(leader)
        self.assertEqual(len(self.s.log), 1)
        self.assertTrue(self.s.log[0].startswith("TE_SELF_CHECK BROKEN mon_union_issuer "), self.s.log[0])

    def test_broken_when_a_modifier_did_not_land(self):
        leader = union(5, adopters=(2e9,))
        self.pulse(leader)
        real_add = self.s.effects["te_monetary_apply_fx_one"]
        # The second pulse finds the cut's modifier gone and cannot put it back.
        del leader.mods["te_mon_union_issuer_premium"]
        self.s.effects["te_monetary_apply_fx_one"] = []
        self.s.execute(self.tail, leader, leader)
        self.s.effects["te_monetary_apply_fx_one"] = real_add
        self.assertTrue(self.s.log[0].startswith("TE_SELF_CHECK BROKEN mon_union_issuer "), self.s.log)

    def test_no_line_from_a_union_with_nothing_to_check(self):
        cases = {"an adopter under 1% of the leader's GDP": union(5, leader_gdp=1e11, adopters=(5e8,)),
                 "no adopter": union(5, adopters=()),
                 "tier 1": union(1),
                 "a leader that cannot issue": union(5, dial=False),
                 "an adopter, not the leader": union(5, adopters=(2e9,)).bloc.members[1]}
        for label, country in cases.items():
            with self.subTest(case=label):
                self.pulse(country)
                self.pulse(country)
                self.assertEqual(self.s.log, [])

    def test_both_lines_name_the_check_and_print_the_figures(self):
        text = (ROOT / UNION_EFFECTS).read_text(encoding="utf-8-sig")
        lines = re.findall(r'debug_log = "(TE_SELF_CHECK (?:OK|BROKEN) mon_union_issuer [^"]*)"', text)
        self.assertEqual(len(lines), 2)
        for line in lines:
            for name in ("te_mon_union_adopters", "te_mon_union_adopter_gdp_m", "te_mon_union_seigniorage_pts",
                         "te_mon_union_issuer_cut_pts"):
                self.assertIn(f"THIS.Var('{name}').GetValue", line)


def principle_blocks():
    out = {}
    for tier in range(1, 6):
        out[tier] = dict((k, v) for k, _, v in definitions(PRINCIPLES)[f"principle_monetary_union_{tier}"])
    return out


def english():
    loc = {}
    for path in sorted(LOC.glob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r'\s+([\w.\-]+):\d*\s+"(.*)"\s*(?:#.*)?$', line)
            if m:
                loc[m.group(1)] = m.group(2)
    return loc


# The principle's display fields (2026-11-15, owner: short names, figures as numeric fields, rules
# in concepts, and each line in the block whose heading names who gets it). Each maps to the first
# tier that carries it; every tier above restates it.
POWER_BLOC_FIELDS = {                                   # Power Bloc: the currency's terms
    "power_bloc_shared_currency_bool": 2,
    "power_bloc_te_mon_currency_trade_advantage_mult": 2,
    "power_bloc_te_mon_currency_investment_pool_add": 2,
    "power_bloc_fiscal_backstop_bool": 3,
    "power_bloc_banking_union_bool": 4,
    "power_bloc_te_mon_currency_crash_chance_mult": 4,
    "power_bloc_te_mon_currency_volatility_mult": 4,
    "power_bloc_te_mon_currency_interventions_add": 4,
    "power_bloc_reserve_currency_bool": 5,
}
NON_LEADER_FIELDS = {                                   # Non-leader Bloc Members: what only members get
    "country_te_mon_swap_premium_add": 1,
    "country_te_mon_swap_confidence_add": 1,
    "country_te_mon_adopter_overvaluation_premium_mult": 3,
    "country_te_mon_adopter_credit_standing_add": 5,
}
LEADER_FIELDS = ("country_te_mon_issuer_seigniorage_gdp_add", "country_te_mon_issuer_premium_add",
                 "country_te_mon_issuer_interventions_add")
CONCEPTS = ("concept_banking_common_currency", "concept_banking_currency_reach")


class TooltipTest(unittest.TestCase):
    """The principle's display fields and the loc's figures are what the script pays."""

    @classmethod
    def setUpClass(cls):
        cls.s = Script()
        cls.blocks = principle_blocks()
        cls.loc = english()
        cls.static = definitions(MODIFIERS)

    def block(self, tier, name):
        return dict((k, float(v) if v != "yes" else v) for k, _, v in self.blocks[tier].get(name, []))

    def leader_block(self, tier):
        return self.block(tier, "leader_modifier")

    def bloc_block(self, tier):
        return self.block(tier, "power_bloc_modifier")

    def members_block(self, tier):
        return self.block(tier, "non_leader_modifier")

    def static_field(self, modifier, key):
        return float(dict((k, v) for k, _, v in self.static[modifier])[key])

    def n(self, name):
        return self.s.number(name, None, None)

    def test_tier_one_promises_the_leader_nothing(self):
        self.assertNotIn("leader_modifier", self.blocks[1])

    def test_each_tier_carries_exactly_its_fields(self):
        for tier in range(1, 6):
            with self.subTest(tier=tier):
                want = {name for name, first in POWER_BLOC_FIELDS.items() if first <= tier}
                self.assertEqual(set(self.bloc_block(tier)) - {"power_bloc_cohesion_per_member_add"}, want)
                for name in want:
                    if name.endswith("_bool"):
                        self.assertEqual(self.bloc_block(tier)[name], "yes")
                self.assertEqual(set(self.members_block(tier)),
                                 {name for name, first in NON_LEADER_FIELDS.items() if first <= tier})
        self.assertNotIn("member_modifier", self.blocks[1], "the swap line skips the leader: non_leader_modifier")

    def test_each_tiers_leader_fields_are_the_script_values(self):
        for tier in (2, 3, 4, 5):
            block = self.leader_block(tier)
            with self.subTest(tier=tier):
                self.assertEqual(set(block), set(LEADER_FIELDS))
                self.assertAlmostEqual(block["country_te_mon_issuer_seigniorage_gdp_add"],
                                       self.n(f"te_mon_union_seigniorage_pct_{tier}") / 100)
                self.assertAlmostEqual(block["country_te_mon_issuer_premium_add"],
                                       -self.n(f"te_mon_union_issuer_cut_max_{tier}") / 100)
                # The issuer's own points; the banking union's is the Power Bloc line's.
                self.assertEqual(block["country_te_mon_issuer_interventions_add"],
                                 self.n(f"te_mon_union_issuer_bank_points_{tier}"))

    def test_the_owners_range_for_tier_five(self):
        # "up to ~3 or 4 at principle V" (owner, 2026-11-14): the issuer's own and the banking union's.
        self.assertEqual(self.leader_block(5)["country_te_mon_issuer_interventions_add"]
                         + self.bloc_block(5)["power_bloc_te_mon_currency_interventions_add"], 4)

    def test_the_swap_line_is_half_a_treaty_one(self):
        self.assertEqual(self.n("te_mon_union_cooperation_share"), 0.5)
        self.assertIn("half a swap line", self.loc["country_te_mon_swap_premium_add_desc"])
        for tier in range(1, 6):
            with self.subTest(tier=tier):
                block = self.members_block(tier)
                self.assertAlmostEqual(block["country_te_mon_swap_premium_add"],
                                       -self.n("te_mon_union_cooperation_cut") / 100)
                self.assertEqual(block["country_te_mon_swap_confidence_add"],
                                 self.n("te_mon_union_cooperation_confidence"))

    def test_the_trade_edge_is_the_adopters_modifiers(self):
        edge = self.static_field("te_mon_union_adopter", "state_export_advantage_mult")
        self.assertEqual(edge, self.static_field("te_mon_union_adopter", "state_import_advantage_mult"))
        reserve = self.static_field("te_mon_union_reserve", "state_export_advantage_mult")
        self.assertEqual(reserve, self.static_field("te_mon_union_reserve", "state_import_advantage_mult"))
        for tier in (2, 3, 4, 5):
            with self.subTest(tier=tier):
                self.assertAlmostEqual(self.bloc_block(tier)["power_bloc_te_mon_currency_trade_advantage_mult"],
                                       edge + (reserve if tier == 5 else 0))

    def test_the_capital_market_by_tier(self):
        unit = self.static_field("te_mon_union_credit", "state_capitalists_investment_pool_contribution_add")
        for tier in (2, 3, 4, 5):
            with self.subTest(tier=tier):
                self.assertAlmostEqual(self.bloc_block(tier)["power_bloc_te_mon_currency_investment_pool_add"],
                                       self.n(f"te_mon_union_credit_points_{tier}") * unit)
        self.assertIn("$too_much_private_construction$",
                      self.loc["power_bloc_te_mon_currency_investment_pool_add_desc"])
        # No text promises more in a slump: the doubling was taken out (owner, 2026-11-14).
        self.assertNotIn("te_mon_union_credit_slump_factor", self.s.values)
        for key in ("power_bloc_te_mon_currency_investment_pool_add_desc", "te_mon_union_adopt_effect_tt",
                    "te_mon_union_credit_desc", *CONCEPTS):
            key = key if key.endswith(("_desc", "_tt")) else key + "_desc"
            with self.subTest(key=key):
                for phrase in ("downturn", "panic", "slump", "twice that", "pull back"):
                    self.assertNotIn(phrase, self.loc[key].lower())

    def test_the_backstop_cuts_the_overvaluation_premium_by_its_figure(self):
        s = Script()
        s.values.update(definitions("common/script_values/te_monetary_fx_script_values.txt"))

        def premium(tier):
            member = next(m for m in union(tier).bloc.members if m.name == "adopter0")
            member.vars["te_mon_overvaluation"] = 15
            return s.number("te_mon_premium_union_overvaluation", member, member)

        self.assertGreater(premium(2), 0)
        for tier in (3, 4, 5):
            with self.subTest(tier=tier):
                cut = self.members_block(tier)["country_te_mon_adopter_overvaluation_premium_mult"]
                self.assertAlmostEqual(premium(tier), premium(2) * (1 + cut))

    def test_the_banking_union_is_its_modifier(self):
        for tier in (4, 5):
            block = self.bloc_block(tier)
            for display, real in (("power_bloc_te_mon_currency_crash_chance_mult", "country_banking_crash_chance_mult"),
                                  ("power_bloc_te_mon_currency_volatility_mult", "country_banking_random_momentum_mult"),
                                  ("power_bloc_te_mon_currency_interventions_add",
                                   "country_banking_intervention_max_add")):
                with self.subTest(tier=tier, field=display):
                    self.assertAlmostEqual(block[display], self.static_field("te_mon_union_banking_union", real))

    def test_the_reserve_tier(self):
        self.assertAlmostEqual(self.members_block(5)["country_te_mon_adopter_credit_standing_add"],
                               -self.n("te_mon_union_reserve_standing_cut") / 100)
        # "...is doubled": the leader's reserve-currency cap at tier 5 against the ordinary one.
        self.assertEqual(self.n("te_mon_reserve_currency_cap_tier_5"), 2 * self.n("te_mon_reserve_currency_cap"))
        self.assertIn("doubled", self.loc["power_bloc_reserve_currency_bool_desc"])

    def test_the_display_fields_are_registered_named_and_described(self):
        types = {
            "power_bloc": (ROOT / "common/modifier_type_definitions/power_bloc_extra_modifier_types.txt")
            .read_text(encoding="utf-8-sig"),
            "country": (ROOT / "common/modifier_type_definitions/banking_cycle_modifier_types.txt")
            .read_text(encoding="utf-8-sig"),
        }
        for name in (*POWER_BLOC_FIELDS, *NON_LEADER_FIELDS, *LEADER_FIELDS):
            with self.subTest(type=name):
                self.assertRegex(types["country" if name.startswith("country") else "power_bloc"],
                                 rf"(?m)^{name} = \{{")
                self.assertIn(name, self.loc)
                self.assertIn(name + "_desc", self.loc)
                # A figure is the field's value, never words in its name.
                self.assertNotRegex(self.loc[name], r"\d")
        for concept in CONCEPTS:
            with self.subTest(concept=concept):
                self.assertIn(concept, self.loc)
                self.assertIn(concept + "_desc", self.loc)

    def test_the_paragraph_markers_are_gone(self):
        for name in ("power_bloc_monetary_cooperation_bool", "country_te_mon_issuer_bool"):
            with self.subTest(name=name):
                self.assertNotIn(name, self.loc)
                for path in ("common/modifier_type_definitions/power_bloc_extra_modifier_types.txt",
                             "common/modifier_type_definitions/banking_cycle_modifier_types.txt", PRINCIPLES):
                    self.assertNotRegex((ROOT / path).read_text(encoding="utf-8-sig"), rf"(?m)^\s*{name} = ")

    def test_the_new_modifiers_are_named_and_described(self):
        for name in ("te_mon_union_issuer_premium", "te_mon_union_issuer_bank", "te_mon_union_credit"):
            with self.subTest(modifier=name):
                self.assertIn(name, self.loc)
                self.assertIn(name + "_desc", self.loc)

    def test_the_reach_figure_in_the_text(self):
        half = self.n("te_mon_union_reach_half_share") * 100
        self.assertIn(f"#v {half:g}%#!", self.loc["concept_banking_currency_reach_desc"])
        for key in ("country_te_mon_issuer_seigniorage_gdp_add_desc", "country_te_mon_issuer_premium_add_desc"):
            with self.subTest(key=key):
                self.assertIn("[concept_banking_currency_reach]", self.loc[key])

    def test_the_budget_texts_give_the_issuers_points(self):
        top = max(self.n(f"te_mon_union_issuer_bank_points_{t}") for t in (2, 3, 4, 5))
        self.assertEqual(top, 3)
        for key in ("banking_dash_budget_tt", "concept_banking_intervention_budget_desc"):
            with self.subTest(key=key):
                self.assertIn("gains up to three more", self.loc[key])

    def test_the_issuer_note_has_its_empty_twin(self):
        self.assertIn("te_mon_union_reach_pct_display", self.loc["banking_dash_mon_union_issuer_note"])
        self.assertEqual(self.loc["banking_dash_mon_union_issuer_note_none"], "")
        self.assertIn("[Country.GetCustom('te_mon_union_issuer_note')]", self.loc["banking_dash_mon_union_tt"])

    def test_reach_as_a_percentage(self):
        leader = union(3, leader_gdp=1e10, adopters=(1.5e9,))
        self.assertTrue(math.isclose(self.s.number("te_mon_union_reach_pct_display", leader, leader), 50))


class MintingBonusTest(unittest.TestCase):
    """The seigniorage is a flat minting add, so the leader's minting bonuses multiply it
    (owner, 2026-11-14: keep them, and say so). Every figure the game states is BEFORE those
    bonuses. The tooltip gives the ceiling; the player guide names each bonus with its size
    (2026-11-15: the tooltip's list of every law, technology and band went with the owner's
    rule that a modifier's text is short). The engine checks none of it: a law or a technology
    that changes its bonus, or a sixth source, would leave the tooltip, the guide and the
    design note quietly wrong again, as they were by 1.3 to 1.75 times when the review of
    PR #1810 found it."""

    KEY = "country_minting_mult"

    @classmethod
    def setUpClass(cls):
        cls.s = Script()
        cls.loc = english()
        cls.desc = cls.loc["country_te_mon_issuer_seigniorage_gdp_add_desc"]
        cls.guide = " ".join((ROOT / "docs/player_guide/04-banking.md").read_text(encoding="utf-8").split())

    def grants(self, body):
        return [float(v) for key, _, block in body if key == "modifier" for k, _, v in block if k == self.KEY]

    def laws(self):
        """{law: bonus} for every law that moves minting: the mod's files, and vanilla's as parsed."""
        import json
        out = {}
        for path in sorted((ROOT / "common/laws").glob("*.txt")):
            for name, body in definitions(str(path.relative_to(ROOT))).items():
                if isinstance(body, list) and self.grants(body):
                    out[name.split(":")[-1]] = sum(self.grants(body))
        for name, (_, body) in json.loads((ROOT / "vanilla_parsed/common/laws.json").read_text(encoding="utf-8")).items():
            if self.KEY in body.get("modifier", ["=", {}])[1]:
                out.setdefault(name, float(body["modifier"][1][self.KEY][1]))
        return out

    def technologies(self):
        """{technology: bonus}: vanilla's as parsed, then whatever the mod's files add or inject."""
        import json
        out = {}
        parsed = json.loads((ROOT / "vanilla_parsed/common/technologies.json").read_text(encoding="utf-8"))
        for name, (_, body) in parsed.items():
            if self.KEY in body.get("modifier", ["=", {}])[1]:
                out[name] = float(body["modifier"][1][self.KEY][1])
        for path in sorted((ROOT / "common/technology/technologies").glob("*.txt")):
            for name, _, body in parse_body(path.read_text(encoding="utf-8-sig")):
                if isinstance(body, list) and self.grants(body):
                    out[name.split(":")[-1]] = out.get(name.split(":")[-1], 0) + sum(self.grants(body))
        return out

    def test_the_seigniorage_is_a_flat_minting_add(self):
        # The premise of "before minting bonuses": were it paid any other way, the text would be wrong.
        effects = [(k, v) for k, _, v in definitions(MODIFIERS)["te_mon_union_seigniorage"] if k != "icon"]
        self.assertEqual(effects, [("country_minting_add", "1")])

    def test_every_figure_is_named_as_before_the_bonuses(self):
        # The field's name is a label (2026-11-15); its hover says the figure is before the bonuses.
        self.assertIn("before its bonuses to [concept_budget_minting]", self.desc)
        self.assertIn("before our bonuses to [concept_budget_minting]", self.loc["te_mon_union_seigniorage_desc"])
        paid = self.loc["banking_dash_mon_union_issuer_note_paid"]
        self.assertLess(paid.index("te_mon_union_seigniorage_base_display"), paid.index("before its bonuses"))
        self.assertLess(paid.index("before its bonuses"), paid.index("te_mon_union_seigniorage_paid_display"))

    def test_the_money_laws_bonuses_are_the_ones_stated(self):
        laws = self.laws()
        self.assertEqual(laws, {"law_fiat_currency": 0.1, "law_digital_currency": 0.25},
                         "a law's minting bonus changed, or another law has one: the seigniorage text names them")
        names = {"law_fiat_currency": "Fiat Money", "law_digital_currency": "Digital Currency"}
        self.assertIn(" or ".join(f"{bonus * 100:g}% under {names[law]}" for law, bonus in laws.items()), self.guide)
        # An issuer is on one of the two, never both: the test of who can lead.
        lead = self.s.triggers["te_mon_can_lead_union"]
        self.assertIn(("OR", "=", [("has_law_or_variant", "=", "law_type:law_fiat_currency"),
                                   ("has_law_or_variant", "=", "law_type:law_digital_currency")]), lead)

    def test_the_technologies_bonuses_are_the_ones_stated(self):
        techs = self.technologies()
        self.assertEqual(len(techs), 5, f"the technologies that move minting changed: {sorted(techs)}")
        self.assertEqual(set(techs.values()), {0.1})
        self.assertIn("10% for each of the five finance technologies", self.guide)
        self.assertIn("all five finance technologies", self.desc)

    def test_the_inflation_bands_cuts_are_the_ones_stated(self):
        static = definitions(MODIFIERS)
        bands = {name: float(v) for name, body in static.items() if name.startswith("te_inflation_band_")
                 for k, _, v in body if k == self.KEY}
        self.assertEqual(bands, {"te_inflation_band_very_high": -0.3, "te_inflation_band_hyper": -0.8})
        self.assertIn(f"Very High inflation takes {-bands['te_inflation_band_very_high'] * 100:g} points off the bonus "
                      f"and Hyperinflation {-bands['te_inflation_band_hyper'] * 100:g}", self.guide)

    def ceiling(self):
        """The most the law and the technologies add: the dearer law and every technology."""
        return max(self.laws().values()) + sum(self.technologies().values())

    def test_the_stated_ceiling_is_the_sum(self):
        top = self.ceiling()
        self.assertAlmostEqual(top, 0.75)
        self.assertIn(f"With $law_digital_currency$ and all five finance technologies the leader mints "
                      f"#v {top * 100:g}%#! more", self.desc)
        self.assertEqual(max(self.laws(), key=self.laws().get), "law_digital_currency")

    def test_the_guide_and_the_design_note_give_the_same_ceiling(self):
        top = self.ceiling()
        most = self.s.number("te_mon_union_seigniorage_pct_5", None, None) * (1 + top)
        self.assertAlmostEqual(most, 2.625)
        guide = " ".join((ROOT / "docs/player_guide/04-banking.md").read_text(encoding="utf-8").split())
        self.assertIn("before minting bonuses", guide)
        self.assertIn(f"up to {top * 100:g}% more", guide)
        self.assertIn(f"about {most:.1f}% of its GDP a year", guide)
        design = " ".join((ROOT / "docs/systems/monetary_policy_design.md").read_text(encoding="utf-8").split())
        self.assertIn(f"1.5% × {1 + top:g} = {most:g}% of GDP a year", design)
        values = " ".join((ROOT / UNION_VALUES).read_text(encoding="utf-8-sig").split())
        self.assertIn(f"1.5% x {1 + top:g} = {most:g}% of GDP a year", values)

    def test_what_the_dashboard_shows_before_and_with_the_bonuses(self):
        leader = union(5)
        self.assertEqual(self.s.number("te_mon_union_seigniorage_base_display", leader, leader), 0)
        leader.vars["te_mon_union_seigniorage_applied"] = 1000
        for bonus, paid in ((0.75, 1750), (0.6, 1600), (0, 1000), (-0.2, 800), (-1.3, 0)):
            leader.sums = {self.KEY: bonus}
            with self.subTest(bonus=bonus):
                self.assertEqual(self.s.number("te_mon_union_seigniorage_base_display", leader, leader), 1000)
                self.assertAlmostEqual(self.s.number("te_mon_union_seigniorage_paid_display", leader, leader), paid)

    def test_the_owners_singapore_mints_what_the_save_shows(self):
        # 1957: Digital Currency and all five technologies, +75%. Its minting line read 526,476 a
        # week: 500, the GDP term's 200,000, 100,250 from currency boards and 93.18 of the old
        # union seigniorage, times 1.75. The multiplier reaches a script-added flat add.
        self.assertAlmostEqual((500 + 200_000 + 100_250 + 93.18) * (1 + self.ceiling()), 526_476, delta=1)
        leader = union(5, leader_gdp=SGP_GDP, adopters=(SGP_ADOPTERS_M * 1e6,))
        leader.vars["te_mon_anchored_gdp_m"] = SGP_ANCHORED_M
        leader.vars["te_mon_union_seigniorage_applied"] = self.s.number("te_mon_union_seigniorage_value", leader, leader)
        leader.sums = {self.KEY: self.ceiling()}
        paid = self.s.number("te_mon_union_seigniorage_paid_display", leader, leader)
        self.assertTrue(18.3e6 < paid < 18.5e6, paid)

    def test_the_note_gives_both_figures_to_an_issuer_that_is_paid(self):
        block = definitions("common/customizable_localization/banking_dash_custom_loc.txt")["te_mon_union_issuer_note"]
        texts = [val for key, _, val in block if key == "text"]
        self.assertEqual([field(t, "localization_key") for t in texts],
                         ["banking_dash_mon_union_issuer_note_paid", "banking_dash_mon_union_issuer_note",
                          "banking_dash_mon_union_issuer_note_none"])
        self.assertEqual(field(texts[0], "trigger"), [("te_mon_union_is_issuer", "=", "yes"),
                                                      ("te_mon_union_seigniorage_base_display", ">", "0")])
        self.assertTrue(self.loc["banking_dash_mon_union_issuer_note_paid"]
                        .startswith("$banking_dash_mon_union_issuer_note$"))



class OtherMintingFiguresTest(MintingBonusTest):
    """The same rule for the two other figures the mod pays as a flat minting add (#1812, item 5):
    Monetizing the Deficit and the overlord's currency-board seigniorage. The engine multiplies
    each by 1 + country_minting_mult, as it does the union's seigniorage, so a text that gives
    the figure must say it is before those bonuses. PR #1810 said so for the union's only.

    Inherits MintingBonusTest's readers and its tests, which then run a second time here."""

    def static(self, name):
        return [(k, v) for k, _, v in definitions(MODIFIERS)[name] if k != "icon"]

    def test_both_are_flat_minting_adds(self):
        # The premise: paid any other way, "before bonuses" would be the wrong thing to say.
        for name in ("te_monetisation_minting", "te_mon_board_seigniorage"):
            with self.subTest(modifier=name):
                self.assertEqual(self.static(name), [("country_minting_add", "1")])

    def test_each_stated_figure_is_named_as_before_the_bonuses(self):
        for key, phrase in (("country_te_mon_minting_gdp_add_desc", "before your bonuses to [concept_budget_minting]"),
                            ("te_monetisation_minting_desc", "before your bonuses to [concept_budget_minting]"),
                            ("te_mon_bond_support_tt", "before our bonuses to [concept_budget_minting]"),
                            ("te_mon_board_seigniorage_desc", "before our bonuses to [concept_budget_minting]")):
            with self.subTest(key=key):
                self.assertIn(phrase, self.loc[key])

    def test_the_step_states_its_share_of_gdp_and_the_text_qualifies_it(self):
        # The one percent is the display field's and the script value's; the qualifier follows it.
        values = definitions("common/script_values/te_monetary_script_values.txt")
        share = float(field(values["te_mon_monetisation_gdp_share"], "value"))
        step = dict(self.static("te_mon_monetisation_step"))
        self.assertEqual(float(step["country_te_mon_minting_gdp_add"]), share)
        tooltip = self.loc["te_mon_bond_support_tt"]
        figure = f"#b {share * 100:g}%#!"
        self.assertLess(tooltip.index(figure), tooltip.index("before our bonuses"))

    def test_the_monetizers_ceiling_is_the_laws_and_the_technologies(self):
        top = self.ceiling()
        desc = self.loc["country_te_mon_minting_gdp_add_desc"]
        self.assertIn(f"with $law_digital_currency$ and all five finance technologies you mint #v {top * 100:g}%#! more", desc)
        # A monetizer is on Fiat Money or Digital Currency, so the dearer law's bonus is reachable.
        triggers = definitions("common/scripted_triggers/te_monetary_triggers.txt")
        self.assertIn(("OR", "=", [("has_law_or_variant", "=", "law_type:law_fiat_currency"),
                                   ("has_law_or_variant", "=", "law_type:law_digital_currency")]),
                      triggers["te_mon_can_monetise"])
        # ...and the two bands the text names are the two that cut minting.
        for band in ("te_inflation_band_very_high", "te_inflation_band_hyper"):
            self.assertIn(f"${band}$", desc)
            self.assertIn(band, self.loc)
            self.assertLess(float(dict(self.static(band))[self.KEY]), 0)

    def test_the_board_takes_half_of_the_flat_sum_from_each_side(self):
        # The overlord's half is half the subject's flat adds, read before any multiplier; the
        # subject's half is fifty points off its multiplier. "Half of what it mints before its
        # bonuses" is true of both, and "half its minting" of neither once the subject has bonuses.
        values = definitions("common/script_values/te_monetary_arrangement_script_values.txt")
        share = float(field(values["te_mon_board_seigniorage_share"], "value"))
        self.assertEqual(share, 0.5)
        self.assertEqual(values["te_mon_board_seigniorage_from_subject"][0], ("value", "=", "modifier:country_minting_add"))
        self.assertEqual(self.static("te_mon_board_subject"), [("country_minting_mult", f"{-share:g}")])
        self.assertIn("mints before its own bonuses", self.loc["te_mon_board_seigniorage_desc"])
        self.assertIn("half of what the country mints before its bonuses", self.loc["banking_dash_mon_why_board"])
        guide = " ".join((ROOT / "docs/player_guide/04-banking.md").read_text(encoding="utf-8").split())
        self.assertIn("half of what the subject mints before its bonuses goes to the overlord", guide)

    def test_the_guide_says_so_for_printing(self):
        self.assertIn("Each level mints about 1% of a year's GDP before minting bonuses", self.guide)


if __name__ == "__main__":
    unittest.main()
