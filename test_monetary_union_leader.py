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
* the common capital market by tier, in a slump and on a pool that cannot be
  spent;
* step 9b applied end to end: the modifiers go on, follow the tier, and come
  off the pulse the leader stops qualifying;
* the principle's display fields and the loc's figures against the script.
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
        self.cycle_running = True
        self.recession = False

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
        self.triggers = definitions("common/scripted_triggers/te_monetary_arrangement_triggers.txt")
        self.triggers.update(definitions(UNION_TRIGGERS))
        self.effects = definitions("common/scripted_effects/te_monetary_fx_effects.txt")
        self.effects.update(definitions(UNION_EFFECTS))
        self.globals = {} if world_gdp_m is None else {"te_mon_world_gdp_m": world_gdp_m}
        self.stub_values = {}       # script values a scenario fixes instead of running
        self.stub_triggers = {}     # likewise triggers
        self.log = []               # debug_log lines, in order

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
        if key == "banking_cycle_is_recession":
            return scope.recession == yes
        if (key == "root" and op == "?=" and val == "this") or (key == "this" and val == "root"):
            return scope is root
        if key == "te_mon_mod_has":
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
            elif key == "set_variable":
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
        # The figures the loc gives (country_te_mon_issuer_bool, the seigniorage field's desc).
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

    def test_a_tier_five_leader_with_only_treaty_peggers_still_earns(self):
        # As the old tier-5 seigniorage did: a reserve currency nobody in its own bloc has adopted.
        leader = union(5, adopters=())
        leader.vars["te_mon_anchored_gdp_m"] = 800
        self.assertGreater(self.s.number("te_mon_union_seigniorage_value", leader, leader), 0)
        self.assertEqual(self.s.number("te_mon_union_seigniorage_value", union(4, adopters=()), None), 0)

    def test_singapore_1957(self):
        # The owner's save: 98 pounds a week before, of a weekly income of 821 million.
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
        cases = {"no bloc": Country("alone", 1e9),
                 "tier 1": union(1),
                 "no dial": union(5, dial=False),
                 "on gold": union(5, laws=("law_national_bank", "law_gold_standard")),
                 "no adopter": union(4, adopters=()),
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
    """te_mon_union_credit_value: adopters and the issuer, by tier, doubled in a slump, and
    nothing where the pool cannot be spent."""

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

    def test_twice_as_much_in_a_downturn_or_panic(self):
        leader = union(5)
        leader.recession = True
        self.assertEqual(self.credit(leader), 10)
        # A dormant banking entry has no cycle to be in a slump: the guard comes first.
        leader.cycle_running = False
        self.assertEqual(self.credit(leader), 5)

    def test_at_tier_five_a_slump_cancels_the_downturns_cut(self):
        # financial_cycle_phase_downturn takes 0.10 off capitalists' contribution.
        downturn = dict((k, v) for k, _, v in definitions(MODIFIERS)["financial_cycle_phase_downturn"])
        unit = float(dict((k, v) for k, _, v in definitions(MODIFIERS)["te_mon_union_credit"])
                     ["state_capitalists_investment_pool_contribution_add"])
        leader = union(5)
        leader.recession = True
        self.assertAlmostEqual(self.credit(leader) * unit,
                               -float(downturn["state_capitalists_investment_pool_contribution_add"]))

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
        self.s.execute(self.tail, country, country)

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
        # The trackers the next pulse compares against.
        self.assertEqual(leader.vars["te_mon_union_issuer_bank_applied"], 3)
        self.assertEqual(leader.vars["te_mon_union_credit_applied"], 5)

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
        # An adopter under the same law keeps the banking union, as it always has.
        member = leader.bloc.members[1]
        member.laws = set(laws)
        self.pulse(member)
        self.assertIn("te_mon_union_banking_union", member.mods)

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
        def exit_all(leader):
            for member in leader.bloc.members[1:]:
                member.vars["te_mon_anchor_kind"] = 0
            leader.vars["te_mon_anchored_gdp_m"] = 0
        self.assertEqual(self.removal(exit_all).mods, {})

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
        self.s.execute(self.tail, leader, leader)

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


class TooltipTest(unittest.TestCase):
    """The principle's display fields and the loc's figures are what the script pays."""

    @classmethod
    def setUpClass(cls):
        cls.s = Script()
        cls.blocks = principle_blocks()
        cls.loc = english()

    def leader_block(self, tier):
        return dict((k, float(v) if v != "yes" else v) for k, _, v in self.blocks[tier]["leader_modifier"])

    def test_tier_one_promises_the_leader_nothing(self):
        self.assertNotIn("leader_modifier", self.blocks[1])

    def test_each_tiers_display_fields_are_the_script_values(self):
        union_point = float(dict((k, v) for k, _, v in definitions(MODIFIERS)["te_mon_union_banking_union"])
                            ["country_banking_intervention_max_add"])
        for tier in (2, 3, 4, 5):
            block = self.leader_block(tier)
            n = lambda name: self.s.number(name.format(tier), None, None)        # noqa: E731
            with self.subTest(tier=tier):
                self.assertEqual(block["country_te_mon_issuer_bool"], "yes")
                self.assertAlmostEqual(block["country_te_mon_issuer_seigniorage_gdp_add"],
                                       n("te_mon_union_seigniorage_pct_{}") / 100)
                self.assertAlmostEqual(block["country_te_mon_issuer_premium_add"],
                                       -n("te_mon_union_issuer_cut_max_{}") / 100)
                self.assertEqual(block["country_te_mon_issuer_interventions_add"],
                                 n("te_mon_union_issuer_bank_points_{}") + (union_point if tier >= 4 else 0))
                self.assertEqual(set(block), {"country_te_mon_issuer_bool", "country_te_mon_issuer_seigniorage_gdp_add",
                                              "country_te_mon_issuer_premium_add",
                                              "country_te_mon_issuer_interventions_add"})

    def test_the_owners_range_for_tier_five(self):
        # "up to ~3 or 4 at principle V" (owner, 2026-11-14).
        self.assertEqual(self.leader_block(5)["country_te_mon_issuer_interventions_add"], 4)

    def test_the_display_fields_are_registered_and_named(self):
        types = (ROOT / "common/modifier_type_definitions/banking_cycle_modifier_types.txt").read_text(encoding="utf-8-sig")
        for name in ("country_te_mon_issuer_bool", "country_te_mon_issuer_seigniorage_gdp_add",
                     "country_te_mon_issuer_premium_add", "country_te_mon_issuer_interventions_add"):
            with self.subTest(type=name):
                self.assertRegex(types, rf"(?m)^{name} = \{{")
                self.assertIn(name, self.loc)

    def test_the_new_modifiers_are_named_and_described(self):
        for name in ("te_mon_union_issuer_premium", "te_mon_union_issuer_bank", "te_mon_union_credit"):
            with self.subTest(modifier=name):
                self.assertIn(name, self.loc)
                self.assertIn(name + "_desc", self.loc)

    def test_the_reach_figure_in_the_text(self):
        half = self.s.number("te_mon_union_reach_half_share", None, None) * 100
        self.assertIn(f"#v {half:g}%#!", self.loc["country_te_mon_issuer_bool"])
        self.assertIn(f"#v {half:g}%#!", self.loc["country_te_mon_issuer_seigniorage_gdp_add_desc"])

    def test_the_capital_markets_figures_in_the_three_tier_lines(self):
        # Tier 5 prints all three lines, so their figures add up to the tier's own.
        points = {t: self.s.number(f"te_mon_union_credit_points_{t}", None, None) for t in (2, 3, 4, 5)}
        self.assertEqual(points[2], points[3], "tier 3's line gives no figure of its own")
        cap = "$state_capitalists_investment_pool_contribution_add$"
        for key, figure in (("power_bloc_shared_currency_bool", points[2]),
                            ("power_bloc_banking_union_bool", points[4] - points[3]),
                            ("power_bloc_reserve_currency_bool", points[5] - points[4])):
            with self.subTest(key=key):
                self.assertIn(f"#G +{figure:g}%#! {cap}", self.loc[key])
        self.assertEqual(self.s.number("te_mon_union_credit_slump_factor", None, None), 2)
        self.assertIn("twice that in a downturn or panic", self.loc["power_bloc_shared_currency_bool"])
        self.assertIn("$too_much_private_construction$", self.loc["power_bloc_shared_currency_bool"])

    def test_the_adopters_trade_figure_in_the_text(self):
        edge = float(dict((k, v) for k, _, v in definitions(MODIFIERS)["te_mon_union_adopter"])
                     ["state_export_advantage_mult"]) * 100
        self.assertIn(f"#G +{edge:g}%#! export and import advantage", self.loc["power_bloc_shared_currency_bool"])

    def test_the_budget_texts_give_the_issuers_points(self):
        top = max(self.s.number(f"te_mon_union_issuer_bank_points_{t}", None, None) for t in (2, 3, 4, 5))
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


if __name__ == "__main__":
    unittest.main()
