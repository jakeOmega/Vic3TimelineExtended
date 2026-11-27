# -*- coding: utf-8 -*-
"""An overdrawn intervention budget lifts tools until it balances (2026-11-14).

Every intervention in force holds its cost in points
(``country_banking_intervention_max_add``, negative on the tool's modifier),
and ``banking_crash_check_overdrawn_interventions`` (banking_cycle_effects.txt,
the banking entry's monthly pulse) lifts one a month while the sum is below
zero. Until 2026-11-14 its chain ended at the five External & Currency tools,
so a budget cut left every other tool running on points the country no longer
had: enact a generous banking law, switch the tools on, go back to Unregulated
Banking and keep them. The points a common currency gives its issuer come and
go with the bloc, so they would have run through the same hole.

The engine checks none of this: a tool the chain leaves out simply stays on.
So:

* every modifier that holds points is in the chain, except the Bank Holiday,
  which is left to run out its ninety days;
* each branch asks for the tool it lifts, and lifts it with that tool's own
  history marker;
* the chain's earlier branches are as they were, and the standing tools follow
  them cheapest first within each economy's family;
* one tool a pulse, and only while the budget is overdrawn;
* the cycle simulator's port lifts in the same order.

A pulse is one effect, and a modifier removed in an effect is still read by the
rest of it (review of PR #1810, finding B). The chain is the pulse's last step,
so a tool an earlier step lifted that month is still in the budget it reads:
after a law change the directed-credit cap or the Outflow Controls cleanup could
balance the budget and the chain lift a second tool regardless. So:

* every step before the chain that lifts a tool holding points marks the pulse
  (``banking_overdraft_wait_a_pulse``), found by walking the steps, the effects
  they call and the events they fire; nothing the chain itself calls does;
* the chain does nothing in a marked pulse but clear the mark;
* the reviewer's two law changes and the Emergency Liquidity wind-down, run
  through the real script with the pulse's opening budget frozen, lift exactly
  what they should, and pay the program's refund once.

And a player is told (finding C): every branch names its tool to
``banking_overdraft_told``, whose notice has its message type, its text and a
name for every tool.
"""

import functools
import re
import unittest
from collections import Counter
from pathlib import Path

from test_monetary_union_leader import Script, definitions, parse_body, substitute

ROOT = Path(__file__).resolve().parent
EFFECT = "banking_crash_check_overdrawn_interventions"
WAIT = "banking_overdraft_wait_a_pulse"         # the effect an earlier step calls where it lifts
WAIT_VAR = "banking_overdraft_wait"             # the variable it sets, and the chain clears
TOLD = "banking_overdraft_told"                 # the notice's helper, called by every branch
POINTS = "country_banking_intervention_max_add"
MODIFIERS = "common/static_modifiers/extra_modifiers.txt"
EFFECT_FILES = ("common/scripted_effects/banking_cycle_effects.txt",
                "common/scripted_effects/banking_policy_effects.txt",
                "common/scripted_effects/banking_external_effects.txt",
                "common/scripted_effects/extra_effects.txt")
LEFT_OUT = {"banking_bank_holiday": "timed: it ends on its own within ninety days"}
FAMILIES = (("banking_", "market"), ("planning_", "command"), ("cooperative_", "coop"))


def field(body, name):
    return next(val for key, _, val in body if key == name)


@functools.lru_cache(maxsize=None)
def parsed(path):
    """definitions(path), parsed once. Never changed by a caller: copy before editing."""
    return definitions(path)


def point_holders():
    """{modifier: cost} for every static modifier with a negative points line."""
    holders = {}
    for name, body in parsed(MODIFIERS).items():
        for key, _, val in body:
            if key == POINTS and float(val) < 0:
                holders[name] = -float(val)
    return holders


def pulse_steps():
    """The effects the banking entry runs each month while its cycle runs, in order."""
    entry = parsed("common/journal_entries/je_banking.txt")["je_banking_cycle"]
    effect = field(field(entry, "on_monthly_pulse"), "effect")
    (dormant, _, _), (running, _, steps) = effect
    assert (dormant, running) == ("if", "else"), "a dormant branch, then the running cycle's steps"
    assert all(val == "yes" for _, _, val in steps), "each step is a bare scripted effect"
    return [key for key, _, _ in steps]


def tool_triggers():
    """{trigger: modifier} for the banking_tool_*_active family (market_triggers.txt)."""
    out = {}
    text = (ROOT / "common/scripted_triggers/market_triggers.txt").read_text(encoding="utf-8-sig")
    for m in re.finditer(r"(?m)^(banking_tool_\w+_active)\s*=\s*\{ je:je_banking_cycle \?= \{ has_modifier = (\w+) \} \}", text):
        out[m.group(1)] = m.group(2)
    return out


def disable_effects():
    """{modifier: (effect name, off marker)} from every banking_effect_*_disable_* pair."""
    out = {}
    for path in ("common/scripted_effects/banking_policy_effects.txt",
                 "common/scripted_effects/banking_external_effects.txt"):
        for name, body in parsed(path).items():
            if not re.match(r"banking_effect_c[bew]_disable_", name):
                continue
            mark = modifier = None
            for key, _, val in body:
                if key == "te_history_record_banking_marker":
                    mark = field(val, "MARK")
                elif key == "je:je_banking_cycle":
                    for k, _, v in val:
                        if k == "remove_modifier":
                            modifier = v
            if modifier:
                out[modifier] = (name, mark)
    return out


def chain():
    """The chain's branches in order: (the modifier asked for, how it is lifted, marker or None)."""
    body = parsed("common/scripted_effects/banking_cycle_effects.txt")[EFFECT]
    assert [key for key, _, _ in body] == ["if", "else_if"], "the marked pulse, else the guarded chain"
    assert body[0][2] == [("limit", "=", [("has_variable", "=", WAIT_VAR)]), ("remove_variable", "=", WAIT_VAR)], \
        "a marked pulse clears the mark and lifts nothing, whatever the budget reads"
    guard = body[1][2]
    limit = field(guard, "limit")
    assert limit == [("modifier:country_banking_intervention_max_add", "<", "0")], limit
    triggers, disables = tool_triggers(), disable_effects()
    by_effect = {effect: modifier for modifier, (effect, _) in disables.items()}
    branches = []
    keys = [key for key, _, _ in guard if key != "limit"]
    assert keys[0] == "if" and set(keys[1:]) == {"else_if"}, "one if, then else_ifs: one lift a pulse"
    for key, _, val in guard:
        if key == "limit":
            continue
        (asked, _, answer), = field(val, "limit")
        assert answer == "yes" or asked == "has_modifier", (asked, answer)
        asked_modifier = answer if asked == "has_modifier" else triggers[asked]
        (action, _, arg), told = [item for item in val if item[0] != "limit"]
        assert told == (TOLD, "=", [("TOOL", "=", asked_modifier)]), \
            f"the branch that lifts {asked_modifier} names it to {TOLD}, and nothing else: {told}"
        if action == "remove_modifier":
            lifted, how, mark = arg, "remove", None
        elif action == "banking_strip_tool":
            lifted, how, mark = field(arg, "MODIFIER"), "strip", field(arg, "MARK")
        else:
            lifted, how, mark = by_effect[action], "disable", disables[by_effect[action]][1]
        assert lifted == asked_modifier, f"the branch asks for {asked_modifier} and lifts {lifted}"
        branches.append((lifted, how, mark))
    return branches


class ChainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.holders = point_holders()
        cls.chain = chain()
        cls.order = [modifier for modifier, _, _ in cls.chain]

    def test_every_tool_that_holds_points_is_in_the_chain(self):
        self.assertGreater(len(self.holders), 45)
        missing = sorted(set(self.holders) - set(self.order) - set(LEFT_OUT))
        self.assertEqual(missing, [], "these hold intervention points and are never lifted on an overdraft")
        self.assertEqual(sorted(set(self.order) - set(self.holders)), [], "in the chain, but holds no points")
        self.assertEqual(len(self.order), len(set(self.order)), "a tool is in the chain twice")

    def test_the_bank_holiday_is_the_one_tool_left_out(self):
        self.assertEqual(set(self.holders) - set(self.order), set(LEFT_OUT))

    def test_the_branches_that_were_there_come_first_and_unchanged(self):
        # Crash interventions (bare removes), then the External & Currency tools through
        # their own Disable: exactly what an overdraft did before the standing tools joined.
        crash = [m for m, how, _ in self.chain if how == "remove"]
        self.assertEqual(self.order[:len(crash)], crash)
        self.assertTrue(all(m.startswith("banking_crash_intervention_") for m in crash))
        self.assertEqual(sorted(crash), sorted(m for m in self.holders if m.startswith("banking_crash_intervention_")))
        external = self.order[len(crash):len(crash) + 5]
        self.assertEqual(external, ["banking_emergency_import_financing", "banking_sterilize_inflows",
                                    "banking_fx_surrender", "banking_restrict_inflows",
                                    "banking_foreign_borrowing_limits"])
        self.assertTrue(all(how == "disable" for _, how, _ in self.chain[len(crash):len(crash) + 5]))

    def standing(self):
        crash = sum(1 for _, how, _ in self.chain if how == "remove")
        return self.chain[crash + 5:]

    def test_the_standing_tools_go_cheapest_first_within_each_family(self):
        standing = [m for m, _, _ in self.standing()]
        seen = []
        for prefix, _ in FAMILIES:
            family = [m for m in standing if m.startswith(prefix)]
            costs = [self.holders[m] for m in family]
            with self.subTest(family=prefix):
                self.assertGreater(len(family), 7)
                self.assertEqual(costs, sorted(costs), f"not cheapest first: {list(zip(family, costs))}")
            seen += family
        # The families are not interleaved (a country runs one at a time).
        self.assertEqual(standing, seen)

    def test_a_standing_tool_is_lifted_as_a_law_lifts_it(self):
        # banking_strip_tool: the history marker and none of the Disable's reactions; the
        # marker is the one the tool's own Disable writes. Emergency Liquidity goes through
        # its Disable, for the refund of what it lent.
        disables = disable_effects()
        for modifier, how, mark in self.standing():
            with self.subTest(tool=modifier):
                self.assertEqual(mark, disables[modifier][1], "not the tool's own off marker")
                if modifier == "banking_emergency_liquidity_program":
                    self.assertEqual(how, "disable")
                else:
                    self.assertEqual(how, "strip")
        eliq = dict((k, v) for k, _, v in parsed("common/scripted_effects/banking_policy_effects.txt")
                    ["banking_effect_cb_disable_emergency_liquidity_program"])
        self.assertEqual(eliq.get("add_treasury"), "emergency_liquidity_program_deactivation_refund")

    def test_the_strip_helper_costs_nothing(self):
        strip = parsed("common/scripted_effects/extra_effects.txt")["banking_strip_tool"]
        (key, _, body), = strip
        self.assertEqual(key, "if")
        # The tool's week-long switch-on mark goes with it (#1811), which costs nothing either.
        self.assertEqual([k for k, _, _ in body], ["limit", "te_history_record_banking_marker", "je:je_banking_cycle",
                                                   "banking_tool_clear_pending"])


class PulseTest(unittest.TestCase):
    """One lift a pulse, in the chain's order, and none on a balanced budget."""

    def lifted(self, active, budget):
        if budget >= 0:
            return None
        return next((m for m, _, _ in chain() if m in active), None)

    def test_one_tool_a_month_until_the_budget_balances(self):
        holders = point_holders()
        # A central bank at 12 points holding 11, which loses the issuer's four.
        active = {"banking_expand_deposit_guarantee", "banking_reserve_requirements",
                  "banking_raise_margin_requirements", "banking_countercyclical_capital_buffer",
                  "banking_moral_suasion"}
        total, lifts = 8, []
        while True:
            budget = total - sum(holders[m] for m in active)
            gone = self.lifted(active, budget)
            if gone is None:
                break
            lifts.append(gone)
            active.discard(gone)
        self.assertEqual(lifts, ["banking_moral_suasion", "banking_reserve_requirements"])
        self.assertEqual(total - sum(holders[m] for m in active), 0)
        self.assertIn("banking_expand_deposit_guarantee", active, "the dearest tool is the last to go")

    def test_a_crash_intervention_goes_before_any_standing_tool(self):
        active = {"banking_moral_suasion", "banking_crash_intervention_open_market"}
        self.assertEqual(self.lifted(active, -1), "banking_crash_intervention_open_market")

    def test_a_balanced_budget_lifts_nothing(self):
        self.assertIsNone(self.lifted({"banking_moral_suasion"}, 0))

    def test_a_bank_holiday_alone_is_left_to_expire(self):
        self.assertIsNone(self.lifted({"banking_bank_holiday"}, -2))


# --------------------------------------------------------------------------------------
# Finding B: the steps before the chain, and the budget the chain reads
# --------------------------------------------------------------------------------------

class Index:
    """Top-level blocks of a folder of script, found by name and parsed a file at a time."""

    def __init__(self, folder, name=r"\w+"):
        self.where = {}
        for path in sorted((ROOT / folder).glob("*.txt")):
            rel = str(path.relative_to(ROOT))
            for found in re.findall(rf"(?m)^({name})\s*=\s*\{{", path.read_text(encoding="utf-8-sig")):
                self.where.setdefault(found, rel)

    def __contains__(self, name):
        return name in self.where

    def __getitem__(self, name):
        return parsed(self.where[name])[name]


class LiftWalk:
    """Every removal of a point-holding modifier that a block of effects can reach, through
    the scripted effects it calls and the `immediate` of the events it fires with no delay.

    A lift is COVERED when a block that encloses it, in the same effect or in a caller, also
    calls WAIT: the mark is then set whenever the lift runs. `uncovered` returns the rest, each
    as the trail of calls that reaches it."""

    DELAYS = {"days", "weeks", "months", "years"}

    def __init__(self, marks=True):
        self.marks = marks                      # False: ignore the marks, to list every lift
        self.holders = set(point_holders())
        self.effects = Index("common/scripted_effects")
        self.events = Index("events", name=r"[\w]+\.\d+")
        self.memo, self.open = {}, set()

    def callee(self, key, body, trail):
        if key in self.open:                    # a loop of effects: nothing new on the way round
            return []
        if key not in self.memo:
            self.open.add(key)
            self.memo[key] = self.uncovered(body, ())
            self.open.discard(key)
        return [trail + rest for rest in self.memo[key]]

    def uncovered(self, body, trail):
        found = []
        for key, _, val in body:
            if key in ("limit", "trigger", "modifier"):       # triggers and weights: no effects
                continue
            if key == "remove_modifier" and val in self.holders:
                found.append(trail + (f"remove_modifier = {val}",))
            elif key == "trigger_event":
                if isinstance(val, list):
                    if self.DELAYS & {k for k, _, _ in val}:
                        continue                # a later day is a later effect
                    event = field(val, "id")
                else:
                    event = val
                immediate = [v for k, _, v in self.events[event] if k == "immediate"]
                for block in immediate:
                    found += self.callee(("event", event), block, trail + (f"{event} immediate",))
            elif key in self.effects:
                params = tuple(sorted((k, v) for k, _, v in val if isinstance(v, str))) if isinstance(val, list) else ()
                body_of = substitute(self.effects[key], dict(params))
                found += self.callee((key, params), body_of, trail + (key,))
            elif isinstance(val, list):
                found += self.uncovered(val, trail + (key,))
        if self.marks and any(key == WAIT for key, _, _ in body):
            return []
        return found


def monthly_on_actions():
    """{on_action: its effect blocks} for everything the mod hangs on a monthly pulse, the
    country's and the global one, through nested on_actions lists."""
    hooks, defs = [], {}
    for path in sorted((ROOT / "common/on_actions").glob("*.txt")):
        for key, _, val in parse_body(path.read_text(encoding="utf-8-sig")):
            if not isinstance(val, list):
                continue
            if key in ("on_monthly_pulse_country", "on_monthly_pulse"):
                hooks.append(val)           # declared in many files: each adds to the hook
            else:
                defs.setdefault(key, []).extend(val)
    out, queue = {}, []
    for body in hooks:
        for key, _, val in body:
            if key == "on_actions":
                queue += [name for name, _, _ in val]
            elif key == "effect":
                out.setdefault("the hook itself", []).append(val)
    while queue:
        name = queue.pop()
        if name in out or name not in defs:
            continue
        out[name] = [val for key, _, val in defs[name] if key == "effect"]
        for key, _, val in defs[name]:
            if key == "on_actions":
                queue += [sub for sub, _, _ in val]
    return out


class EarlierStepsTest(unittest.TestCase):
    """Whatever lifts a tool before the chain, in the same pulse, marks the pulse."""

    LIFTING = {"banking_cycle_eliq_wind_down", "banking_cycle_cleanup_capital_controls",
               "banking_directed_credit_enforce_cap"}

    @classmethod
    def setUpClass(cls):
        cls.steps = pulse_steps()

    def step_body(self, step):
        return [(step, "=", "yes")]

    def test_the_chain_is_the_pulses_last_step(self):
        # A step after it would read the budget before the chain's own lift, not after.
        self.assertEqual(self.steps[-1], EFFECT)
        self.assertEqual(self.steps.count(EFFECT), 1)
        text = "".join(p.read_text(encoding="utf-8-sig") for p in sorted((ROOT / "common").rglob("*.txt"))
                       if "scripted_effects" in p.parts or "journal_entries" in p.parts or "on_actions" in p.parts)
        self.assertEqual(len(re.findall(rf"(?m)^\s*{EFFECT} = yes", text)), 1, "the chain has one caller")

    def test_the_three_steps_that_lift_tools_are_found(self):
        # With the marks ignored the walk must see the lifts, or the next test proves nothing.
        walk = LiftWalk(marks=False)
        lifting = {step for step in self.steps[:-1] if walk.uncovered(self.step_body(step), ())}
        self.assertEqual(lifting, self.LIFTING,
                         "the steps before the chain that lift a point-holding tool changed: check each marks "
                         "the pulse where it lifts, and list it here")
        # ...and the walk follows a call into the helper that does the removing.
        eliq = walk.uncovered(self.step_body("banking_cycle_eliq_wind_down"), ())
        self.assertEqual(eliq, [("banking_cycle_eliq_wind_down", "if", "if", "if",
                                 "banking_effect_cb_disable_emergency_liquidity_program", "je:je_banking_cycle",
                                 "remove_modifier = banking_emergency_liquidity_program")])

    def test_every_lift_before_the_chain_marks_the_pulse(self):
        walk = LiftWalk()
        for step in self.steps[:-1]:
            with self.subTest(step=step):
                self.assertEqual(walk.uncovered(self.step_body(step), ()), [],
                                 f"lifts a tool that holds points and does not call {WAIT} beside it: the "
                                 "overdraft chain reads this pulse's opening budget")

    def test_every_lift_from_a_monthly_on_action_marks_the_month(self):
        # The monetary update runs from the country's monthly on_action, the same day as the
        # entry's pulse and in an order nobody has measured. It lifts External & Currency tools
        # that are no longer eligible or funded, and all five when the banking rule leaves Full.
        # Whether such a lift has reached the sum the chain reads is not verified, so each marks.
        actions = monthly_on_actions()
        self.assertGreater(len(actions), 60)
        seen, marked = LiftWalk(marks=False), LiftWalk()
        lifting = set()
        for name, effects in actions.items():
            for effect in effects:
                if seen.uncovered(effect, ()):
                    lifting.add(name)
                with self.subTest(on_action=name):
                    self.assertEqual(marked.uncovered(effect, (name,)), [],
                                     f"lifts a tool that holds points and does not call {WAIT} beside it")
        self.assertEqual(lifting, {"te_monetary_monthly_on_action"},
                         "the monthly on_actions that lift a point-holding tool changed")
        lifts = {trail[-1].split(" = ")[1] for effect in actions["te_monetary_monthly_on_action"]
                 for trail in seen.uncovered(effect, ())}
        self.assertEqual(lifts, {"banking_restrict_inflows", "banking_sterilize_inflows", "banking_fx_surrender",
                                 "banking_foreign_borrowing_limits", "banking_emergency_import_financing"})

    def test_a_lift_with_no_mark_is_caught(self):
        # The same walk on a step that forgot: the Outflow Controls cleanup without its mark.
        walk = LiftWalk()
        cleanup = [item for item in substitute(walk.effects["banking_cycle_cleanup_capital_controls"], {})]
        (key, op, body), = cleanup
        stripped = [(key, op, [item for item in body if item[0] != WAIT])]
        self.assertEqual(len(walk.uncovered(stripped, ())), 1)

    def test_each_marked_step_marks_only_where_it_lifts(self):
        # The mark sits in the branch that removes, so a pulse that lifted nothing is not held.
        for step in sorted(self.LIFTING):
            blocks = []

            def collect(body):
                if any(key == WAIT for key, _, _ in body):
                    blocks.append(body)
                for _, _, val in body:
                    if isinstance(val, list):
                        collect(val)
            collect(parsed("common/scripted_effects/banking_cycle_effects.txt")[step])
            with self.subTest(step=step):
                self.assertTrue(blocks)
                walk = LiftWalk(marks=False)
                for block in blocks:
                    own = [item for item in block if item[0] not in ("if", "else_if", "else")]
                    self.assertTrue(walk.uncovered(own, ()), f"a mark with no lift beside it in {step}")

    def test_nothing_the_chain_calls_marks_the_pulse(self):
        # It would hold its own next pulse, and an overdraft would shed every second month.
        seen = set()

        def calls(body, effects):
            for key, _, val in body:
                if key in effects and key not in seen:
                    seen.add(key)
                    params = {k: v for k, _, v in val if isinstance(v, str)} if isinstance(val, list) else {}
                    calls(substitute(effects[key], params), effects)
                elif isinstance(val, list):
                    calls(val, effects)
        effects = Index("common/scripted_effects")
        calls(effects[EFFECT], effects)
        self.assertIn("banking_strip_tool", seen)
        self.assertIn("banking_effect_cb_disable_emergency_liquidity_program", seen)
        self.assertNotIn(WAIT, seen)

    def test_the_mark_is_a_variable_write(self):
        # Visible at once, unlike the modifier it stands for.
        self.assertEqual(parsed("common/scripted_effects/banking_cycle_effects.txt")[WAIT],
                         [("set_variable", "=", WAIT_VAR)])


class Bank:
    """A country and its banking entry, as the monthly pulse reads them."""

    def __init__(self, laws, tools, *, ai=False, at_war=False, **variables):
        self.laws = set(laws) | {"law_national_bank"}
        self.entry = Counter(tools)             # the entry's modifiers: the tools in force
        self.own = Counter()                    # the country's own: crash interventions
        self.vars = {"finance_cycle_value": 60.0, **variables}
        self.ai, self.at_war = ai, at_war
        self.markers, self.notices, self.paid, self.errors = [], [], [], []
        self.cycle_running = True

    def __repr__(self):
        return "bank"


class Pulse(Script):
    """The steps of the monthly pulse that lift tools, and the chain, run from the real script.

    THE ENGINE'S RULE: a modifier removed in an effect is still there for the rest of that effect.
    So every `modifier:` sum is the one the pulse opened with, and with stale_has_modifier so is
    every has_modifier (the lessons disagree on how far that reaches; the fix must hold either way).
    """

    def __init__(self, stale_has_modifier):
        super().__init__()
        self.values = dict(self.values)
        self.values.update(parsed("common/script_values/extra_script_values.txt"))
        self.effects = {}
        for path in EFFECT_FILES:
            self.effects.update(parsed(path))
        self.static = parsed(MODIFIERS)
        self.law_defs = parsed("common/laws/extra_laws.txt")
        self.stale_has_modifier = stale_has_modifier
        walk = LiftWalk(marks=False)
        self.steps = [step for step in pulse_steps()
                      if step == EFFECT or walk.uncovered([(step, "=", "yes")], ())]
        self.opening = None
        self.locals = {}
        self.in_entry = False

    # ------------------------------------------------------------------ reads
    def total(self, name, bank, entry, own):
        """A country's modifier sum: its laws', the entry's and its own."""
        n = 0.0
        for law in bank.laws:
            for key, _, val in self.law_defs[law]:
                if key == "modifier":
                    n += sum(float(v) for k, _, v in val if k == name)
        for mods in (entry, own):
            for mod, count in mods.items():
                n += count * sum(float(v) for k, _, v in self.static[mod] if k == name)
        return n

    def budget(self, bank):
        """The true sum, as the next effect will read it."""
        return self.total(POINTS, bank, bank.entry, bank.own)

    def has(self, bank, modifier):
        entry, own = self.opening if self.stale_has_modifier else (bank.entry, bank.own)
        return (entry if self.in_entry else own)[modifier] > 0

    def number(self, value, scope, root):
        if isinstance(value, str):
            if value.startswith("modifier:"):
                return self.total(value[len("modifier:"):], scope, *self.opening)
            if value.startswith("local_var:"):
                return self.locals[value[len("local_var:"):]]
        return super().number(value, scope, root)

    def test(self, key, op, val, scope, root):
        yes = val == "yes"
        if key == "je:je_banking_cycle":
            self.in_entry = True
            try:
                return self.check(val, scope, root)
            finally:
                self.in_entry = False
        if key == "has_modifier":
            return self.has(scope, val)
        if key == "has_law":
            return val.removeprefix("law_type:") in scope.laws
        if key == "is_at_war":
            return scope.at_war == yes
        if key == "is_ai":
            return scope.ai == yes
        return super().test(key, op, val, scope, root)

    # ---------------------------------------------------------------- effects
    def lift(self, bank, mods, modifier):
        if mods[modifier] <= 0:
            bank.errors.append(f"removed a modifier that was already gone: {modifier}")
            return
        mods[modifier] -= 1
        if not mods[modifier]:
            del mods[modifier]

    def statement(self, key, val, scope, root):
        if key == "set_variable" and isinstance(val, str):
            scope.vars[val] = True
        elif key == "set_variable" and str(field(val, "value")).startswith("flag:"):
            scope.vars[field(val, "name")] = field(val, "value")
        elif key == "set_local_variable":
            self.locals[field(val, "name")] = self.number(field(val, "value"), scope, root)
        elif key == "change_local_variable":
            self.locals[field(val, "name")] += self.number(field(val, "add"), scope, root)
        elif key == "je:je_banking_cycle":
            (inner, _, modifier), = val
            assert inner == "remove_modifier", inner
            self.lift(scope, scope.entry, modifier)
        elif key == "remove_modifier":
            self.lift(scope, scope.own, val)
        elif key == "te_history_record_banking_marker":
            scope.markers.append(field(val, "MARK"))
        elif key == "hidden_effect":
            self.execute(val, scope, root)
        elif key == "add_treasury":
            scope.paid.append(val)
        elif key == "post_notification":
            scope.notices.append(val)
        else:
            super().statement(key, val, scope, root)

    def pulse(self, bank):
        """One month: every step sees the modifiers the pulse opened with."""
        self.opening = (Counter(bank.entry), Counter(bank.own))
        self.locals = {}
        for step in self.steps:
            self.run(step, bank)
        self.opening = None


class StalePulseTest(unittest.TestCase):
    """The reviewer's cases. Each runs twice: with has_modifier live, and stale like the sums."""

    UNIVERSAL = "law_universal_banking_light_prudence"

    def each(self):
        for stale in (False, True):
            with self.subTest(has_modifier="stale" if stale else "live"):
                yield Pulse(stale)

    def test_the_steps_run_are_the_lifting_ones_then_the_chain(self):
        self.assertEqual(Pulse(False).steps, ["banking_cycle_eliq_wind_down", "banking_cycle_cleanup_capital_controls",
                                              "banking_directed_credit_enforce_cap", EFFECT])

    def test_the_budgets_the_cases_stand_on(self):
        p = Pulse(False)
        self.assertEqual(p.budget(Bank({"law_directed_credit_development_banks"}, ())), 6)
        self.assertEqual(p.budget(Bank({self.UNIVERSAL}, ())), 5)
        self.assertEqual(p.budget(Bank({"law_prudential_narrow_banking"}, ())), 8)

    def test_a_cap_that_balances_the_budget_is_the_only_lift(self):
        # Directed Credit & Development Banks, 6 points and two sectors: Agriculture credit (2),
        # Infrastructure credit (3), Moral Suasion (1). Then Universal Banking: 5 points, one sector.
        for p in self.each():
            bank = Bank({self.UNIVERSAL}, ("banking_directed_credit_agriculture",
                                           "banking_directed_credit_infrastructure", "banking_moral_suasion"))
            self.assertEqual(p.budget(bank), -1)
            p.pulse(bank)
            self.assertEqual(sorted(bank.entry), ["banking_directed_credit_infrastructure", "banking_moral_suasion"],
                             "the cap lifts Agriculture, the budget is +1, and nothing else may go")
            self.assertEqual(p.budget(bank), 1)
            self.assertNotIn(WAIT_VAR, bank.vars, "the chain cleared the mark")
            p.pulse(bank)
            self.assertEqual(len(bank.entry), 2, "and the next month finds nothing to do")
            self.assertEqual(bank.markers, ["off_cb_directed_credit_agriculture"])
            self.assertEqual(bank.errors, [])

    def test_a_cleanup_that_balances_the_budget_is_the_only_lift(self):
        # Prudential Banking, 8 points: Outflow Controls (2), Deposit Guarantee (4), Moral Suasion (1).
        # Then Universal Banking, 5 points, whose law forbids the controls in peace.
        for p in self.each():
            bank = Bank({self.UNIVERSAL}, ("banking_capital_controls_out", "banking_expand_deposit_guarantee",
                                           "banking_moral_suasion"))
            self.assertEqual(p.budget(bank), -2)
            p.pulse(bank)
            self.assertEqual(sorted(bank.entry), ["banking_expand_deposit_guarantee", "banking_moral_suasion"])
            self.assertEqual(p.budget(bank), 0)
            p.pulse(bank)
            self.assertEqual(len(bank.entry), 2)
            self.assertEqual(bank.errors, [])

    def test_a_cap_that_leaves_an_overdraft_is_followed_a_month_later(self):
        # The same downgrade with a Deposit Guarantee beside the two sectors: the cap gives back 2
        # of an overdraft of 5, and the chain takes the rest from the next month, on true sums.
        for p in self.each():
            bank = Bank({self.UNIVERSAL}, ("banking_directed_credit_agriculture", "banking_directed_credit_infrastructure",
                                           "banking_expand_deposit_guarantee", "banking_moral_suasion"))
            self.assertEqual(p.budget(bank), -5)
            lifted = []
            for _ in range(6):
                before = set(bank.entry)
                p.pulse(bank)
                lifted.append(sorted(before - set(bank.entry)))
            self.assertEqual(lifted, [["banking_directed_credit_agriculture"], ["banking_moral_suasion"],
                                      ["banking_directed_credit_infrastructure"], [], [], []])
            self.assertEqual(p.budget(bank), 1)
            self.assertEqual(bank.errors, [])

    def winding_down(self, tools, **kw):
        # The cycle has held at stable or above for eleven months: this pulse is the twelfth.
        return Bank({"law_prudential_narrow_banking"}, tools, banking_eliq_recovery_months=11,
                    banking_eliq_announced=True, **kw)

    def test_the_wind_down_and_the_chain_do_not_both_close_the_program(self):
        # Emergency Liquidity (4) and Asset Relief (5) on 8 points: overdrawn by 1, and the program
        # is the first tool the chain would reach. The wind-down closes it the same pulse.
        for p in self.each():
            bank = self.winding_down(("banking_emergency_liquidity_program", "banking_asset_relief_program"))
            self.assertEqual(p.budget(bank), -1)
            p.pulse(bank)
            self.assertEqual(bank.paid, ["emergency_liquidity_program_deactivation_refund"], "the refund, once")
            self.assertEqual(sorted(bank.entry), ["banking_asset_relief_program"],
                             "the wind-down gave four points back: the budget is +3 and Asset Relief stays")
            self.assertEqual(bank.markers, ["off_cb_emergency_liquidity_program"])
            self.assertEqual(bank.notices, ["banking_eliq_wound_down_notice"])
            self.assertEqual(bank.errors, [])
            p.pulse(bank)
            self.assertEqual(sorted(bank.entry), ["banking_asset_relief_program"])
            self.assertEqual(len(bank.paid), 1)

    def test_a_pulse_with_no_earlier_lift_is_not_held(self):
        # The chain's own lifts come a month apart, never two: nothing it calls marks the pulse.
        for p in self.each():
            bank = Bank({self.UNIVERSAL}, ("banking_expand_deposit_guarantee", "banking_reserve_requirements",
                                           "banking_moral_suasion"))
            self.assertEqual(p.budget(bank), -2)
            lifted = []
            for _ in range(4):
                before = set(bank.entry)
                p.pulse(bank)
                lifted.append(sorted(before - set(bank.entry)))
            self.assertEqual(lifted, [["banking_moral_suasion"], ["banking_reserve_requirements"], [], []])

    def test_a_mark_is_cleared_even_when_the_budget_reads_balanced(self):
        # The wind-down in a month with room to spare: the mark must not wait for an overdraft.
        for p in self.each():
            bank = self.winding_down(("banking_emergency_liquidity_program",))
            p.pulse(bank)
            self.assertEqual(bank.entry, Counter())
            self.assertNotIn(WAIT_VAR, bank.vars)

    def test_without_the_mark_the_model_shows_the_fault(self):
        # The harness can fail: the same pulse with the mark's effect emptied lifts Moral Suasion
        # on a budget the cap had already balanced, as the game did.
        for p in self.each():
            p.effects = dict(p.effects)
            p.effects[WAIT] = []
            bank = Bank({self.UNIVERSAL}, ("banking_directed_credit_agriculture",
                                           "banking_directed_credit_infrastructure", "banking_moral_suasion"))
            p.pulse(bank)
            self.assertEqual(sorted(bank.entry), ["banking_directed_credit_infrastructure"])


# --------------------------------------------------------------------------------------
# Finding C: a player is told
# --------------------------------------------------------------------------------------

class NoticeTest(unittest.TestCase):
    NOTICE = "banking_overdraft_lift_notice"
    LOC = ROOT / "localization" / "english"

    @classmethod
    def setUpClass(cls):
        cls.keys = {}
        for path in cls.LOC.glob("*_l_english.yml"):
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                m = re.match(r'\s+([\w\.\-]+):\d*\s*"(.*)"\s*$', line)
                if m:
                    cls.keys[m.group(1)] = m.group(2)
        cls.custom = parsed("common/customizable_localization/banking_dash_custom_loc.txt")

    def test_a_human_is_told_and_the_ai_is_not(self):
        told = parsed("common/scripted_effects/banking_cycle_effects.txt")[TOLD]
        self.assertEqual(told, [("if", "=", [
            ("limit", "=", [("is_ai", "=", "no")]),
            ("set_variable", "=", [("name", "=", "banking_overdraft_lifted"), ("value", "=", "flag:$TOOL$")]),
            ("post_notification", "=", self.NOTICE)])])
        for ai, expected in ((False, [self.NOTICE]), (True, [])):
            p = Pulse(False)
            bank = Bank({"law_universal_banking_light_prudence"},
                        ("banking_expand_deposit_guarantee", "banking_reserve_requirements"), ai=ai)
            p.pulse(bank)
            with self.subTest(ai=ai):
                self.assertEqual(bank.notices, expected)
                self.assertEqual(bank.vars.get("banking_overdraft_lifted"),
                                 None if ai else "flag:banking_reserve_requirements")

    def test_the_notice_is_defined_as_the_mods_feed_notices_are(self):
        message = dict((k, v) for k, _, v in parsed("common/messages/extra_messages.txt")[self.NOTICE])
        self.assertEqual(message, {"type": "country", "notification_type": "feed", "color": "bad",
                                   "texture": "gfx/interface/icons/notification_icons/journal.dds"})

    def test_the_text_names_the_tool_and_the_cause(self):
        desc = self.keys[f"notification_{self.NOTICE}_desc"]
        self.assertIn(f"notification_{self.NOTICE}_name", self.keys)
        self.assertIn("[GetPlayer.GetCustom('banking_overdraft_lifted_tool')]", desc)
        self.assertIn("[GetPlayer.GetCustom('banking_overdraft_lifted_refund')]", desc)
        self.assertIn("[concept_banking_intervention_budget]", desc)
        self.assertIn("no longer covers", desc)
        self.assertIn("$banking_dash_cat_external$", desc, "the tab is named by its own key")
        self.assertIn("banking_dash_cat_external", self.keys)

    def test_every_branch_has_a_name_and_the_name_is_the_tools_own(self):
        block = self.custom["banking_overdraft_lifted_tool"]
        self.assertEqual(dict((k, v) for k, _, v in block if k != "text"), {"type": "country", "random_valid": "no"})
        texts = [val for key, _, val in block if key == "text"]
        named = []
        for text in texts[:-1]:
            (_, _, trigger), (_, _, key) = text
            self.assertEqual(trigger[0], ("has_variable", "=", "banking_overdraft_lifted"))
            (var, op, flag), = trigger[1:]
            self.assertEqual((var, op), ("var:banking_overdraft_lifted", "="))
            tool = flag.removeprefix("flag:")
            self.assertEqual(key, tool, "a tool is named by its modifier's own key")
            self.assertIn(tool, self.keys, f"{tool} has no name")
            self.assertTrue(self.keys[tool])
            named.append(tool)
        self.assertEqual(named, [modifier for modifier, _, _ in chain()], "one name per branch, in the chain's order")
        self.assertEqual(texts[-1], [("localization_key", "=", "banking_overdraft_lifted_tool_unnamed")])
        self.assertTrue(self.keys["banking_overdraft_lifted_tool_unnamed"])

    def test_the_refund_line_is_emergency_liquiditys_alone(self):
        block = self.custom["banking_overdraft_lifted_refund"]
        (first, last) = [val for key, _, val in block if key == "text"]
        self.assertEqual(first, [("trigger", "=", [("has_variable", "=", "banking_overdraft_lifted"),
                                                   ("var:banking_overdraft_lifted", "=",
                                                    "flag:banking_emergency_liquidity_program")]),
                                 ("localization_key", "=", "banking_overdraft_lifted_refund_eliq")])
        self.assertEqual(last, [("localization_key", "=", "banking_overdraft_lifted_refund_none")])
        self.assertEqual(self.keys["banking_overdraft_lifted_refund_none"], "")
        # The figure it states is the Disable's refund.
        refund = dict((k, v) for k, _, v in parsed("common/script_values/extra_script_values.txt")
                      ["emergency_liquidity_program_deactivation_refund"])
        self.assertEqual((refund["value"], float(refund["multiply"])), ("gdp", 0.01))
        self.assertIn("1% of GDP", self.keys["banking_overdraft_lifted_refund_eliq"])
        self.assertTrue(self.keys["banking_overdraft_lifted_refund_eliq"].startswith(" "),
                        "it follows the sentence before it")


class SimulatorPortTest(unittest.TestCase):
    """scripts/analysis/banking_cycle_sim.py's prune_overdrawn_tools lifts in the script's order."""

    def test_the_port_follows_the_chain(self):
        from scripts.analysis import banking_cycle_sim as sim
        names = dict(sim.TOOL_MODIFIER_NAMES)
        names.update(sim.ALT_TOOL_MODIFIER_NAMES)
        order = [m for m, how, _ in chain() if how != "remove"]
        for prefix, economy in FAMILIES:
            script = [m for m in order if m.startswith(prefix)]
            port = [names[tool] for tool in sim.OVERDRAFT_SHED_ORDER[economy]]
            with self.subTest(economy=economy):
                self.assertEqual(port, script)
        self.assertNotIn("bank_holiday", sim.OVERDRAFT_SHED_ORDER["market"])

    def test_the_port_sits_out_the_month_the_wind_down_closed_the_program(self):
        # The script's rule (banking_overdraft_wait_a_pulse): Emergency Liquidity (4) and Asset
        # Relief (5) on 8 points, and the wind-down closes the program on its twelfth month.
        from scripts.analysis import banking_cycle_sim as sim
        cfg = sim.Config(points=8)
        state = sim.State(finance_cycle_value=60.0)
        state.tools = {"eliq", "asset_relief"}
        state.eliq_announced = True
        state.eliq_recovery_months = sim.ELIQ_WIND_DOWN_MONTHS - 1
        self.assertEqual(sim.intervention_points(cfg, state), -1)
        sim.eliq_wind_down(cfg, state)
        self.assertEqual(state.tools, {"asset_relief"})
        self.assertTrue(state.overdraft_wait)
        sim.prune_overdrawn_tools(cfg, state)
        self.assertEqual(state.tools, {"asset_relief"})
        self.assertFalse(state.overdraft_wait, "the mark is cleared the same month")
        # ...and an overdraft the wind-down did not answer is shed from the next month.
        state.tools = {"eliq", "asset_relief", "deposit"}
        state.eliq_announced = True
        state.eliq_recovery_months = sim.ELIQ_WIND_DOWN_MONTHS - 1
        sim.eliq_wind_down(cfg, state)
        sim.prune_overdrawn_tools(cfg, state)
        self.assertEqual(state.tools, {"asset_relief", "deposit"})
        sim.prune_overdrawn_tools(cfg, state)
        self.assertEqual(state.tools, {"asset_relief"})

    def test_the_port_marks_nothing_on_its_own_lift(self):
        from scripts.analysis import banking_cycle_sim as sim
        cfg = sim.Config(points=5)
        state = sim.State()
        state.tools = {"deposit", "reserve_requirements", "moral_suasion"}
        for expected in ({"deposit", "reserve_requirements"}, {"deposit"}, {"deposit"}):
            sim.prune_overdrawn_tools(cfg, state)
            self.assertEqual(state.tools, expected)
            self.assertFalse(state.overdraft_wait)


if __name__ == "__main__":
    unittest.main()
