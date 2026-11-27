"""Batched private investment (docs/systems/mod_systems/construction.md § Batched Private Investment).

When the investors of a very large economy queue a level at home, the mod queues more levels of the same building
beside it, so the engine's weekly investment pass makes a few dozen decisions where it made a thousand
(common/scripted_effects/te_batch_investment_effects.txt). Nothing in the engine checks that script, and three things
it rests on have not been read in game, so this runs the script's own text (the effects, the values, the triggers, the
generated dispatcher and the on-actions) through a small interpreter against a model of the engine's weekly pass:

- as the script assumes the engine behaves (`Engine()`): the pass makes far fewer decisions, the queue never passes the
  engine's 1,000, no batch passes the ceiling, a building is batched once a week, and every self-check reads OK;
- and with each assumption turned off in the model (`hook="after"`, `recheck=False`, `count_first=False`, a refused
  effect, levels queued in answer to a batch): the script stays bounded, and the self-check written for that failure
  says BROKEN. The model is the test's, not the engine's: it shows what the script does if the engine behaves a given
  way, not which way the engine behaves. The game's own lines say that (docs/testing/perf-fixes-playtest.md).

It also keeps the generated files current and the wiring, the rule and its texts whole.

Run: python3 -m pytest test_batch_investment.py
"""

import math
import random
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import gen_batch_investment as gen  # noqa: E402

EFFECTS = ROOT / "common/scripted_effects/te_batch_investment_effects.txt"
GENERATED_EFFECTS = ROOT / gen.EFFECTS
TRIGGERS = ROOT / "common/scripted_triggers/te_batch_investment_triggers.txt"
GENERATED_TRIGGERS = ROOT / gen.TRIGGERS
VALUES = ROOT / "common/script_values/te_batch_investment_values.txt"
ON_ACTIONS = ROOT / "common/on_actions/te_batch_investment_on_actions.txt"
RULES = ROOT / "common/game_rules/extra_game_rules.txt"
RULE_LOC = ROOT / "localization/english/te_game_rules_l_english.yml"
OLD_LIST = ROOT / "common/scripted_triggers/misc_triggers.txt"

OPERATORS = ("<=", ">=", "!=", "?=", "=", "<", ">")


# ---------------------------------------------------------------------------------------------------------------------
# A reader that keeps statement order and quoted strings (the repo's parser groups repeated keys, which loses the
# order an effect runs in).
# ---------------------------------------------------------------------------------------------------------------------
def tokenize(text):
    tokens, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace() or c == "﻿":
            i += 1
        elif c == "#":
            while i < n and text[i] != "\n":
                i += 1
        elif c == '"':
            end = text.index('"', i + 1)
            tokens.append(text[i:end + 1])
            i = end + 1
        elif c in "{}":
            tokens.append(c)
            i += 1
        elif text[i:i + 2] in OPERATORS:
            tokens.append(text[i:i + 2])
            i += 2
        elif c in "=<>":
            tokens.append(c)
            i += 1
        else:
            start = i
            while i < n and not text[i].isspace() and text[i] not in '{}=<>#"' and text[i:i + 2] not in ("!=", "?="):
                i += 1
            tokens.append(text[start:i])
    return tokens


def parse_block(tokens, pos=0):
    """A block's items as (key, op, value) in file order: value a str or a list of items; a bare word is (word, None,
    None)."""
    items = []
    while pos < len(tokens) and tokens[pos] != "}":
        key = tokens[pos]
        if pos + 1 < len(tokens) and tokens[pos + 1] in OPERATORS:
            op = tokens[pos + 1]
            if tokens[pos + 2] == "{":
                value, pos = parse_block(tokens, pos + 3)
                if tokens[pos] != "}":
                    raise ValueError(f"unclosed block under {key!r}")
                pos += 1
            else:
                value, pos = tokens[pos + 2], pos + 3
            items.append((key, op, value))
        else:
            items.append((key, None, None))
            pos += 1
    return items, pos


def read(path):
    tokens = tokenize(path.read_text(encoding="utf-8-sig"))
    items, pos = parse_block(tokens)
    if pos != len(tokens):
        raise ValueError(f"{path.name}: a closing brace too many")
    return items


def top(path):
    return {key: value for key, _, value in read(path)}


def substitute(node, params):
    if isinstance(node, str):
        for name, value in params.items():
            node = node.replace(f"${name}$", value)
        return node
    if isinstance(node, list):
        return [(substitute(k, params), op, substitute(v, params)) for k, op, v in node]
    return node


class Script:
    """The system's script, as written."""

    def __init__(self):
        self.effects = {**top(EFFECTS), **top(GENERATED_EFFECTS)}
        self.triggers = {**top(TRIGGERS), **top(GENERATED_TRIGGERS)}
        self.values = top(VALUES)
        self.on_actions = top(ON_ACTIONS)


# ---------------------------------------------------------------------------------------------------------------------
# The world the script runs in.
# ---------------------------------------------------------------------------------------------------------------------
class Scope:
    def __init__(self):
        self.vars = {}  # name -> (value, the day it expires or None)


class Country(Scope):
    def __init__(self, tag):
        super().__init__()
        self.tag = tag
        self.queue = []  # the private queue: (building, who queued it)
        self.government_queue = 0
        self.gross_income, self.net_income = 1000.0, 0.0


class State(Scope):
    def __init__(self, name, owner):
        super().__init__()
        self.name, self.owner, self.buildings = name, owner, {}


class Building(Scope):
    def __init__(self, kind, state, level, room=None):
        super().__init__()
        self.kind, self.state, self.level = kind, state, level
        self.room = room  # further levels it can take, queued ones counted; None is no cap
        state.buildings[kind] = self

    def queued(self):
        return sum(1 for building, _ in self.state.owner.queue if building is self)


class Engine:
    """The engine as far as the script meets it. The keyword arguments are the assumptions the script rests on; each
    default is the assumed behavior."""

    LIMIT = 1000

    def __init__(self, script, *, hook="inside", script_hook=None, count_first=True, recheck=True, refuse=None,
                 answer=0, rules=()):
        self.script = script
        self.hook = hook  # when on_start_expanding_building runs for a level the engine queues: inside, after, never
        self.script_hook = script_hook or hook  # and for a level script queues
        self.count_first = count_first  # the level is in the queue when its hook runs
        self.recheck = recheck  # the pass reads the queue's length again after each level
        self.refuse = refuse  # a building -> bool: the effect queues nothing for it
        self.answer = answer  # private levels something else queues in answer to each level script queues
        self.rules = set(rules)
        self.day = 0
        self.globals = {}
        self.log = []
        self.waiting = []  # hook calls put off until the pass or the effect is over
        self.depth = 0
        self.flushing = False
        self.decisions = {}  # tag -> the engine's decisions in each weekly pass

    # -- queueing ---------------------------------------------------------------------------------------------------
    def queue_private(self, investor, building, who):
        mode = self.script_hook if who == "script" else self.hook
        if self.count_first:
            investor.queue.append((building, who))
            self.fire(building, mode)
        else:
            self.fire(building, mode)
            investor.queue.append((building, who))

    def queue_government(self, building):
        building.state.owner.government_queue += 1
        self.fire(building, self.hook)

    def fire(self, building, mode):
        if mode == "inside":
            self.run_hook(building)
        elif mode == "after":
            self.waiting.append(building)

    def flush(self):
        """Run the hook calls put off, once no effect is running. A call run here may put off more."""
        if self.depth or self.flushing:
            return
        self.flushing = True
        try:
            while self.waiting:
                self.run_hook(self.waiting.pop(0))
        finally:
            self.flushing = False

    def run_hook(self, building):
        self.run_on_action("te_bi_on_start_expanding", building)

    def run_on_action(self, name, root):
        body = dict((k, v) for k, _, v in self.script.on_actions[name])
        run = Run(self, root)
        if run.cond(body.get("trigger", []), root):
            self.depth += 1
            try:
                run.effect(body["effect"], root)
            finally:
                self.depth -= 1
        self.flush()

    def script_queues(self, state, kind):
        """start_privately_funded_building_construction = <kind>, state scope."""
        building = state.buildings[kind]
        if self.refuse and self.refuse(building):
            return
        if building.room is not None and building.queued() >= building.room:
            return
        self.queue_private(state.owner, building, "script")
        for _ in range(self.answer):
            state.owner.queue.append((building, "answer"))

    # -- the week ---------------------------------------------------------------------------------------------------
    def finish(self, country, levels):
        done, country.queue = country.queue[:levels], country.queue[levels:]
        for building, _ in done:
            building.level += 1

    def invest(self, country, pick, updates=5000):
        """The weekly pass: one level a decision, until the queue is full."""
        decisions = 0
        slots = self.LIMIT - len(country.queue)
        for _ in range(updates):
            if self.recheck and len(country.queue) >= self.LIMIT:
                break
            if not self.recheck and decisions >= slots:
                break
            self.queue_private(country, pick(), "engine")
            decisions += 1
        self.flush()
        self.decisions.setdefault(country.tag, []).append(decisions)
        return decisions

    def monthly(self, country):
        self.run_on_action("te_bi_monthly_on_action", country)

    def lines(self, start):
        return [line for line in self.log if line.startswith(start)]


class Run:
    """One effect, from its root, with its own local variables."""

    def __init__(self, engine, root):
        self.engine, self.script, self.root, self.locals = engine, engine.script, root, {}

    # -- scopes -----------------------------------------------------------------------------------------------------
    @staticmethod
    def link(name, scope):
        if name == "owner":
            return scope.state.owner if isinstance(scope, Building) else scope.owner
        if name == "state" and isinstance(scope, Building):
            return scope.state
        raise ValueError(f"no link {name!r} from {type(scope).__name__}")

    def held(self, scope, name):
        if name not in scope.vars:
            return False
        _, expires = scope.vars[name]
        return expires is None or self.engine.day < expires

    def var(self, scope, name):
        if not self.held(scope, name):
            raise AssertionError(f"var:{name} read on a {type(scope).__name__} that does not hold it")
        return scope.vars[name][0]

    # -- values -----------------------------------------------------------------------------------------------------
    def value(self, raw, scope):
        if isinstance(raw, list):
            return self.body(raw, scope)
        try:
            return float(raw)
        except ValueError:
            pass
        if raw.startswith("local_var:"):
            if raw[10:] not in self.locals:
                raise AssertionError(f"{raw} read before it is set")
            return self.locals[raw[10:]]
        if raw.startswith("global_var:"):
            if raw[11:] not in self.engine.globals:
                raise AssertionError(f"{raw} read while unset")
            return self.engine.globals[raw[11:]]
        if raw.startswith("var:"):
            return self.var(scope, raw[4:])
        if raw in self.script.values:
            return self.value(self.script.values[raw], scope)
        if raw == "level" and isinstance(scope, Building):
            return float(scope.level)
        if isinstance(scope, Country):
            if raw == "construction_queue_num_queued_private_levels":
                return float(len(scope.queue))
            if raw == "investment_pool_gross_income":
                return scope.gross_income
            if raw == "investment_pool_net_income":
                return scope.net_income
        raise AssertionError(f"{raw!r} is not a value a {type(scope).__name__} has")

    def body(self, items, scope):
        x, taken = 0.0, False
        for key, _, val in items:
            if key == "value":
                x = self.value(val, scope)
            elif key == "add":
                x += self.value(val, scope)
            elif key == "subtract":
                x -= self.value(val, scope)
            elif key == "multiply":
                x *= self.value(val, scope)
            elif key == "min":  # a floor
                x = max(x, self.value(val, scope))
            elif key == "max":  # a cap
                x = min(x, self.value(val, scope))
            elif key == "floor":
                x = float(math.floor(x))
            elif key in ("if", "else_if", "else"):
                if key == "if":
                    taken = False
                limit = next((v for k, _, v in val if k == "limit"), [])
                if not taken and (key == "else" or self.cond(limit, scope)):
                    taken = True
                    rest = [item for item in val if item[0] != "limit"]
                    x = self.body([("value", "=", repr(x)), *rest], scope)
            else:
                raise AssertionError(f"script value key {key!r} is not modelled")
            x = round(x, 5)  # the engine's fixed-point numbers
        return x

    # -- triggers ---------------------------------------------------------------------------------------------------
    def cond(self, items, scope):
        return all(self.one(key, op, val, scope) for key, op, val in items)

    def one(self, key, op, val, scope):
        if key == "AND":
            return self.cond(val, scope)
        if key == "OR":
            return any(self.one(k, o, v, scope) for k, o, v in val)
        if key == "NOT":
            if len(val) != 1:
                raise AssertionError("a NOT with several children reads every one of them")
            return not self.cond(val, scope)
        if key in ("owner", "state"):
            return self.cond(val, self.link(key, scope))
        if key == "has_variable":
            return self.held(scope, val)
        if key == "has_global_variable":
            return val in self.engine.globals
        if key == "has_game_rule":
            return val in self.engine.rules
        if key == "is_building_type":
            return scope.kind == val
        if key == "can_queue_building_levels":
            return scope.room is None or scope.queued() + self.value(val, scope) <= scope.room
        if key == "month":
            return compare((self.engine.day // 30) % 12, op, float(val))
        if key in self.script.triggers:
            return self.cond(self.script.triggers[key], scope) == (val == "yes")
        return compare(self.value(key, scope), op, self.value(val, scope))

    # -- effects ----------------------------------------------------------------------------------------------------
    def effect(self, items, scope):
        taken = False
        for key, _op, val in items:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    taken = False
                limit = next((v for k, _, v in val if k == "limit"), [])
                if not taken and (key == "else" or self.cond(limit, scope)):
                    taken = True
                    self.effect([item for item in val if item[0] != "limit"], scope)
            elif key == "while":
                count = self.value(next(v for k, _, v in val if k == "count"), scope)
                if count != int(count) or count > 1000:
                    raise AssertionError(f"while count {count}")
                for _ in range(int(count)):
                    self.effect([item for item in val if item[0] != "count"], scope)
            elif key in ("owner", "state"):
                self.effect(val, self.link(key, scope))
            elif key in ("set_variable", "set_local_variable", "set_global_variable"):
                self.set(key, val, scope)
            elif key in ("change_variable", "change_local_variable", "change_global_variable"):
                self.change(key, dict((k, v) for k, _, v in val), scope)
            elif key == "remove_variable":
                if not self.held(scope, val):
                    raise AssertionError(f"remove_variable = {val}: not set")
                del scope.vars[val]
            elif key == "remove_global_variable":
                if val not in self.engine.globals:
                    raise AssertionError(f"remove_global_variable = {val}: not set")
                del self.engine.globals[val]
            elif key == "debug_log":
                self.engine.log.append(self.render(val.strip('"'), scope))
            elif key == "start_privately_funded_building_construction":
                if not isinstance(scope, State):
                    raise AssertionError("start_privately_funded_building_construction is a state effect")
                self.engine.script_queues(scope, val)
            elif key in self.script.effects:
                params = {} if isinstance(val, str) else {k: v for k, _, v in val}
                self.effect(substitute(self.script.effects[key], params), scope)
            else:
                raise AssertionError(f"effect {key!r} is not modelled")

    def set(self, key, val, scope):
        if isinstance(val, str):  # the flag form
            name, value, expires = val, True, None
        else:
            fields = dict((k, v) for k, _, v in val)
            name = fields["name"]
            value = self.value(fields["value"], scope) if "value" in fields else True
            expires = self.engine.day + int(fields["days"]) if "days" in fields else None
        if key == "set_local_variable":
            self.locals[name] = value
        elif key == "set_global_variable":
            self.engine.globals[name] = value
        else:
            if isinstance(scope, Building):
                raise AssertionError(f"set_variable = {name} on a building: buildings hold no variables")
            scope.vars[name] = (value, expires)

    def change(self, key, fields, scope):
        name = fields["name"]
        delta = self.value(fields["add"], scope) if "add" in fields else -self.value(fields["subtract"], scope)
        if key == "change_local_variable":
            if name not in self.locals:
                raise AssertionError(f"change_local_variable on unset {name}")
            self.locals[name] += delta
        elif key == "change_global_variable":
            if name not in self.engine.globals:
                raise AssertionError(f"change_global_variable on unset {name}")
            self.engine.globals[name] += delta
        else:
            value = self.var(scope, name)
            scope.vars[name] = (value + delta, scope.vars[name][1])

    # -- debug_log --------------------------------------------------------------------------------------------------
    def render(self, text, scope):
        def one(match):
            expression = match.group(1)
            if expression == "THIS.GetCountry.GetTagName":
                return scope.tag
            if expression == "TimeKeeper.GetCurrentDate.GetString":
                return f"day{self.engine.day}"
            named = re.fullmatch(r"(THIS|SCOPE)\.ScriptValue\('(\w+)'\)\|0", expression)
            if named:
                # SCOPE.ScriptValue reads against ROOT, whatever the current scope (scripting_best_practices.md,
                # "`debug_log` Loc-String Templating Limitations").
                return str(int(self.value(named.group(2), scope if named.group(1) == "THIS" else self.root)))
            variable = re.fullmatch(r"THIS\.Var\('(\w+)'\)\.GetValue\|0", expression)
            if variable:
                return str(int(self.var(scope, variable.group(1))))
            raise AssertionError(f"debug_log accessor [{expression}] is not one the guide lists as printing")
        return re.sub(r"\[([^\]]+)\]", one, text)


def compare(lhs, op, rhs):
    return {"=": lhs == rhs, "<": lhs < rhs, ">": lhs > rhs, "<=": lhs <= rhs, ">=": lhs >= rhs, "!=": lhs != rhs}[op]


# ---------------------------------------------------------------------------------------------------------------------
# A very large economy: forty states of city industries, a railway and a power plant in each, and investment abroad.
# ---------------------------------------------------------------------------------------------------------------------
INDUSTRIES = ("building_steel_mill", "building_motor_industry", "building_tooling_workshop", "building_glassworks",
              "building_electrics_industry", "building_chemical_plant", "building_art_academy",
              "building_textile_mill")
LOCAL = ("building_railway", "building_power_plant")


class Giant:
    def __init__(self, engine, *, abroad=0.3, states=40, seed=7):
        self.engine, self.abroad = engine, abroad
        self.random = random.Random(seed)
        self.country, self.host = Country("USA"), Country("MEX")
        self.home, self.foreign = [], []
        for index in range(states):
            state = State(f"home{index}", self.country)
            for kind in INDUSTRIES + LOCAL:
                self.home.append(Building(kind, state, self.random.randint(200, 5000)))
        for index in range(10):
            state = State(f"abroad{index}", self.host)
            for kind in INDUSTRIES:
                self.foreign.append(Building(kind, state, self.random.randint(50, 500)))
        while len(self.country.queue) < Engine.LIMIT:  # the queue as the engine left it last week
            self.country.queue.append((self.pick(), "engine"))

    def pick(self):
        return self.random.choice(self.foreign if self.random.random() < self.abroad else self.home)

    def run(self, days, *, finish=1000, each_day=None):
        """Every seventh day the week's levels finish and the pass refills the queue; every thirtieth is a monthly
        pulse."""
        for _ in range(days):
            engine = self.engine
            if engine.day % 7 == 0:
                engine.finish(self.country, finish)
                engine.invest(self.country, self.pick)
            if engine.day % 30 == 0:
                engine.monthly(self.country)
                engine.monthly(self.host)
            if each_day:
                each_day(self)
            engine.day += 1
            self.check()

    def check(self):
        """What holds on every day in every engine: script never queues past the ceiling, and never abroad."""
        assert not self.host.queue, "a level was queued for the host country"
        assert not self.host.vars, "the host country, never at 200 levels queued, is watched"

    def on(self):
        return "te_bi_on" in self.country.vars

    def var(self, name):
        return self.country.vars[name][0]


SCRIPT = Script()


def constant(name):
    return float(SCRIPT.values[name])


class TheAssumedEngine(unittest.TestCase):
    """The engine as the script assumes it: the hook runs inside the pass with the level counted, and the pass reads
    the queue again after each level."""

    @classmethod
    def setUpClass(cls):
        cls.engine = Engine(SCRIPT)
        cls.giant = Giant(cls.engine)
        cls.giant.run(150)
        cls.before = cls.engine.decisions["USA"][1:5]  # the passes of the first month, watched and not batching
        cls.after = cls.engine.decisions["USA"][9:]  # from the second month of batching

    def test_batching_starts_after_a_month_of_hundreds_of_levels_a_week(self):
        self.assertTrue(self.giant.on())
        self.assertEqual(len(self.engine.lines("TE_BI on country=USA")), 1)
        self.assertIn("day30", self.engine.lines("TE_BI on")[0])

    def test_the_pass_makes_a_small_fraction_of_its_decisions(self):
        self.assertGreater(min(self.before), 900)
        # The reserve's hundred single levels, and a dozen or two batches.
        self.assertLess(max(self.after), constant("te_bi_reserve") + 60)
        self.assertLess(sum(self.after) / len(self.after), 0.15 * sum(self.before) / len(self.before))

    def test_as_many_levels_are_placed_as_before(self):
        # The queue is refilled to the engine's limit every week either way.
        self.assertEqual(len(self.giant.country.queue), Engine.LIMIT)
        self.assertEqual(self.giant.var("te_bi_maxq"), Engine.LIMIT)

    def test_every_self_check_reads_ok(self):
        verdicts = [line.split()[1:3] for line in self.engine.lines("TE_SELF_CHECK") if " START " not in line]
        self.assertEqual(sorted(verdicts), [["OK", "batch_invest_hook"], ["OK", "batch_invest_month"],
                                            ["OK", "batch_invest_queue"], ["OK", "batch_invest_reentry"]])

    def test_each_verdict_follows_its_start_line(self):
        for name in ("batch_invest_queue", "batch_invest_hook", "batch_invest_month"):
            self.assertEqual(len(self.engine.lines(f"TE_SELF_CHECK START {name}")), 1, name)

    def test_the_month_line_prints_each_of_the_first_months(self):
        lines = self.engine.lines("TE_BI month country=USA")
        self.assertEqual(len(lines), 3)  # days 60, 90, 120
        figures = dict(part.split("=") for part in lines[-1].split()[2:])
        self.assertEqual(figures["over"], "0")
        self.assertEqual(figures["short"], "0")
        self.assertEqual(figures["unknown"], "0")
        self.assertGreater(int(figures["added"]), 3000)
        self.assertLess(int(figures["picks_home"]) + int(figures["picks_other"]), 800)


class WhatABatchIs(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(SCRIPT)
        self.giant = Giant(self.engine)
        self.queued, self.level_then = [], {}
        original = self.engine.script_queues

        def spy(state, kind):
            building = state.buildings[kind]
            self.queued.append((self.engine.day, building, len(state.owner.queue)))
            self.level_then.setdefault((self.engine.day, building), building.level)
            original(state, kind)

        self.engine.script_queues = spy
        self.giant.run(100)

    def batches(self):
        grouped = {}
        for day, building, _ in self.queued:
            grouped.setdefault((day, building), []).append(building)
        return grouped

    def test_no_batch_is_queued_before_batching_is_on(self):
        self.assertTrue(self.queued)
        self.assertGreaterEqual(min(day for day, _, _ in self.queued), 30)

    def test_no_level_is_queued_at_or_past_the_ceiling(self):
        self.assertLess(max(length for _, _, length in self.queued), constant("te_bi_engine_queue")
                        - constant("te_bi_reserve"))

    def test_a_batch_is_a_tenth_of_the_building_and_a_fiftieth_for_a_local_good(self):
        sizes = set()
        for key, levels in self.batches().items():
            building, level = key[1], self.level_then[key]  # its built levels when the batch was sized
            total = len(levels) + 1  # the engine's own level
            local = building.kind in LOCAL
            self.assertLessEqual(total, constant("te_bi_local_batch_max" if local else "te_bi_batch_max"))
            self.assertLessEqual(total, level * constant("te_bi_local_share" if local else "te_bi_share"))
            sizes.add((local, total))
        # Both caps are reached by the largest buildings.
        self.assertIn((False, int(constant("te_bi_batch_max"))), sizes)
        self.assertIn((True, int(constant("te_bi_local_batch_max"))), sizes)

    def test_a_building_is_batched_once_a_week(self):
        weeks = {}
        for day, building in self.batches():
            weeks.setdefault((day // 7, building), []).append(day)
        self.assertTrue(all(len(days) == 1 for days in weeks.values()))

    def test_local_goods_buildings_get_batches_too(self):
        self.assertTrue(any(building.kind in LOCAL for _, building in self.batches()))


class TheSizes(unittest.TestCase):
    def size(self, kind, level):
        engine = Engine(SCRIPT)
        building = Building(kind, State("s", Country("AAA")), level)
        return Run(engine, building).value("te_bi_batch_extra", building)

    def test_an_ordinary_building(self):
        self.assertEqual([self.size("building_steel_mill", level) for level in (0, 19, 20, 29, 30, 555, 999, 1000, 9000)],
                         [0, 0, 1, 1, 2, 54, 98, 99, 99])

    def test_a_local_goods_building(self):
        self.assertEqual([self.size("building_railway", level) for level in (0, 99, 100, 149, 150, 499, 500, 9000)],
                         [0, 0, 1, 1, 2, 8, 9, 9])

    def test_the_tuning_is_in_order(self):
        self.assertLess(constant("te_bi_off_levels"), constant("te_bi_on_levels"))
        self.assertLess(constant("te_bi_unwatch_queue"), constant("te_bi_watch_queue"))
        self.assertLess(constant("te_bi_reserve"), constant("te_bi_engine_queue"))
        self.assertLess(constant("te_bi_local_share"), constant("te_bi_share"))
        self.assertLess(constant("te_bi_local_batch_max"), constant("te_bi_batch_max"))
        # A batch's own levels come back through the hook inside one `while`, which the engine stops at 1,000 passes.
        self.assertLess(constant("te_bi_batch_max"), 1000)
        # A country placing te_bi_on_levels a month holds a week's worth in its queue, so it is watched by then.
        self.assertLessEqual(constant("te_bi_watch_queue"), constant("te_bi_on_levels") / 4)


class WithoutTheReserve(unittest.TestCase):
    def test_the_pass_is_left_a_few_dozen_decisions(self):
        script = Script()
        script.values["te_bi_reserve"] = "0"
        engine = Engine(script)
        giant = Giant(engine)
        giant.run(120)
        self.assertLess(max(engine.decisions["USA"][9:]), 60)
        self.assertLessEqual(len(giant.country.queue), Engine.LIMIT + constant("te_bi_batch_max"))


class WhoPlacedTheLevel(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(SCRIPT)
        self.giant = Giant(self.engine)
        self.giant.run(61)  # batching since day 30; day 56's pass has filled the queue

    def test_a_government_level_is_nobodys_pick(self):
        self.engine.queue_government(self.giant.home[0])  # brings var:te_bi_seen up to date
        home, added, queue = self.giant.var("te_bi_home"), self.giant.var("te_bi_added"), len(self.giant.country.queue)
        self.engine.queue_government(self.giant.home[1])
        self.assertEqual((self.giant.var("te_bi_home"), self.giant.var("te_bi_added")), (home, added))
        self.assertEqual(len(self.giant.country.queue), queue)

    def test_with_the_queue_full_a_misread_level_adds_nothing(self):
        # Whatever the last pick of the week's pass was, home or abroad.
        queue = len(self.giant.country.queue)
        self.assertEqual(queue, Engine.LIMIT)
        self.engine.queue_government(self.giant.home[0])
        self.assertEqual(len(self.giant.country.queue), queue)

    def test_a_pick_abroad_is_never_batched(self):
        before = len(self.giant.country.queue)
        self.engine.finish(self.giant.country, 500)
        self.engine.queue_private(self.giant.country, self.giant.foreign[0], "engine")
        self.assertEqual(len(self.giant.country.queue), before - 500 + 1)

    def test_a_government_level_straight_after_a_pick_abroad_is_taken_for_the_investors(self):
        # The limit the effects file states: script reads who queued a level from the private queue's length at the
        # last call at home, and a pick abroad lengthens it without one.
        self.engine.finish(self.giant.country, 500)
        self.engine.queue_government(self.giant.home[0])  # brings var:te_bi_seen up to date
        self.engine.queue_private(self.giant.country, self.giant.foreign[0], "engine")
        before = len(self.giant.country.queue)
        marked = Run(self.engine, self.giant.country).held
        target = next(b for b in self.giant.home if b.kind == "building_steel_mill"
                      and not marked(b.state, "te_bi_m_building_steel_mill"))
        self.engine.queue_government(target)
        self.assertGreater(len(self.giant.country.queue), before)
        self.assertLessEqual(len(self.giant.country.queue), before + constant("te_bi_batch_max") - 1)

    def test_a_capped_building_keeps_its_single_level(self):
        mine = Building("building_gold_mine", self.giant.home[0].state, 400, room=3)
        self.engine.finish(self.giant.country, 500)
        self.engine.queue_government(self.giant.home[1])
        before, capped = len(self.giant.country.queue), self.giant.var("te_bi_capped")
        self.engine.queue_private(self.giant.country, mine, "engine")
        self.assertEqual(len(self.giant.country.queue), before + 1)
        self.assertEqual(self.giant.var("te_bi_capped"), capped + 1)


class ASmallerEconomy(unittest.TestCase):
    def test_under_two_hundred_levels_a_week_nothing_is_batched(self):
        engine = Engine(SCRIPT)
        giant = Giant(engine)
        giant.run(150, finish=150)  # 150 levels finish a week, so the pass places 150
        self.assertFalse(giant.on())
        self.assertFalse(engine.lines("TE_BI on"))
        self.assertTrue(all(decisions == 150 for decisions in engine.decisions["USA"][1:]))

    def test_a_country_with_a_short_queue_is_not_watched(self):
        engine = Engine(SCRIPT)
        giant = Giant(engine)
        giant.country.queue = giant.country.queue[:150]
        engine.monthly(giant.country)
        self.assertFalse(giant.country.vars)
        engine.queue_private(giant.country, giant.home[0], "engine")
        self.assertFalse(giant.country.vars)


class TheRule(unittest.TestCase):
    def test_switched_off_mid_game_batching_stops_at_the_next_level_and_the_counters_go_at_the_pulse(self):
        engine = Engine(SCRIPT)
        giant = Giant(engine)
        giant.run(61)
        self.assertTrue(giant.on())
        engine.rules.add("te_batch_investment_disabled")
        engine.finish(giant.country, 800)
        decisions = engine.invest(giant.country, giant.pick)
        self.assertEqual(decisions, 800)
        engine.monthly(giant.country)
        self.assertFalse(giant.country.vars)

    def test_with_the_rule_off_no_country_is_watched(self):
        engine = Engine(SCRIPT, rules=["te_batch_investment_disabled"])
        giant = Giant(engine)
        giant.run(90)
        self.assertFalse(giant.country.vars)
        self.assertFalse(engine.log)

    def test_the_rule_and_its_texts(self):
        rule = dict((k, v) for k, _, v in top(RULES)["te_batch_investment_rule"])
        self.assertEqual(rule["default"], "te_batch_investment_enabled")
        for setting in ("te_batch_investment_enabled", "te_batch_investment_disabled"):
            self.assertEqual(rule[setting], [("flag", "=", setting)])
        loc = RULE_LOC.read_text(encoding="utf-8-sig")
        for key in ("rule_te_batch_investment_rule", "setting_te_batch_investment_enabled",
                    "setting_te_batch_investment_enabled_desc", "setting_te_batch_investment_disabled",
                    "setting_te_batch_investment_disabled_desc"):
            self.assertRegex(loc, rf"(?m)^ {key}:0 \"")

    def test_a_game_begun_before_the_rule_plays_with_batching_on(self):
        # Such a save names no setting: both triggers read the disabled one.
        self.assertEqual(SCRIPT.triggers["te_bi_rule_on"],
                         [("NOT", "=", [("has_game_rule", "=", "te_batch_investment_disabled")])])
        self.assertEqual(SCRIPT.triggers["te_bi_rule_off"], [("has_game_rule", "=", "te_batch_investment_disabled")])


class IfTheEngineDiffers(unittest.TestCase):
    """Each assumption turned off in the model: the script stays bounded and its line says what failed."""

    def verdicts(self, engine):
        return {line.split()[2]: line.split()[1] for line in engine.lines("TE_SELF_CHECK") if " START " not in line}

    def test_the_hook_runs_after_the_pass(self):
        engine = Engine(SCRIPT, hook="after")
        giant = Giant(engine)
        giant.run(240)
        self.assertFalse(giant.on())
        self.assertEqual(self.verdicts(engine), {"batch_invest_hook": "BROKEN"})
        self.assertTrue(all(decisions == 1000 for decisions in engine.decisions["USA"][1:]))

    def test_the_hook_never_runs_for_a_private_level(self):
        engine = Engine(SCRIPT, hook="never")
        giant = Giant(engine)
        giant.run(240)
        self.assertFalse(giant.on())
        self.assertEqual(self.verdicts(engine), {"batch_invest_hook": "BROKEN"})

    def test_a_stalled_full_queue_is_not_called_broken(self):
        engine = Engine(SCRIPT, hook="never")
        giant = Giant(engine)
        giant.country.gross_income = giant.country.net_income = 0.0  # the pool pays for nothing
        giant.run(240, finish=0)
        self.assertEqual(self.verdicts(engine), {})

    def test_the_pass_does_not_read_the_queue_again(self):
        engine = Engine(SCRIPT, recheck=False)
        giant = Giant(engine)
        giant.run(120)
        self.assertEqual(self.verdicts(engine)["batch_invest_month"], "BROKEN")
        # Bounded all the same: script stops at the ceiling, and the engine adds its thousand.
        self.assertLessEqual(len(giant.country.queue), 2 * Engine.LIMIT)
        self.assertGreater(giant.var("te_bi_maxq"), Engine.LIMIT)

    def test_the_hook_runs_before_the_level_is_counted(self):
        engine = Engine(SCRIPT, count_first=False)
        giant = Giant(engine)
        giant.run(120)
        self.assertEqual(self.verdicts(engine).get("batch_invest_reentry"), "BROKEN")
        self.assertLessEqual(len(giant.country.queue), Engine.LIMIT + constant("te_bi_batch_max"))

    def test_scripts_own_levels_reach_the_hook_later(self):
        engine = Engine(SCRIPT, script_hook="after")
        giant = Giant(engine)
        giant.run(120)
        verdicts = self.verdicts(engine)
        self.assertEqual(verdicts["batch_invest_reentry"], "NO_VERDICT")
        self.assertEqual(verdicts["batch_invest_queue"], "OK")
        self.assertEqual(verdicts["batch_invest_month"], "OK")
        # The late calls find the queue as the batch left it, and batch nothing.
        self.assertLessEqual(len(giant.country.queue), Engine.LIMIT)
        self.assertLess(max(engine.decisions["USA"][9:]), constant("te_bi_reserve") + 60)

    def test_the_effect_queues_nothing_from_the_hook(self):
        engine = Engine(SCRIPT, refuse=lambda building: True)
        giant = Giant(engine)
        giant.run(120)
        self.assertEqual(self.verdicts(engine)["batch_invest_queue"], "BROKEN")
        self.assertIn("queued=0", engine.lines("TE_SELF_CHECK BROKEN batch_invest_queue")[0])
        month = engine.lines("TE_BI month")[0]
        self.assertNotIn("short=0 ", month)

    def test_levels_queued_in_answer_to_a_batch_trip_it_for_good(self):
        engine = Engine(SCRIPT, answer=1)
        giant = Giant(engine)
        giant.run(120)
        self.assertEqual(len(engine.lines("TE_SELF_CHECK BROKEN batch_invest_runaway")), 1)
        self.assertIn("te_bi_tripped", engine.globals)
        self.assertFalse(giant.on())
        # One batch, twice its size, and no more.
        self.assertEqual(sum(1 for _, who in giant.country.queue if who == "script"), 0)
        self.assertLessEqual(len(giant.country.queue), Engine.LIMIT)
        self.assertEqual(len(engine.lines("TE_BI on")), 1)

    def test_a_flag_left_up_is_cleared_and_reported(self):
        engine = Engine(SCRIPT)
        giant = Giant(engine)
        giant.run(61)
        engine.globals["te_bi_placing"] = 0.0
        engine.finish(giant.country, 800)
        self.assertEqual(engine.invest(giant.country, giant.pick), 800)  # every level passed over
        engine.monthly(giant.country)
        self.assertNotIn("te_bi_placing", engine.globals)
        self.assertEqual(len(engine.lines("TE_SELF_CHECK BROKEN batch_invest_flag")), 1)


class ARevolution(unittest.TestCase):
    def test_the_winner_inherits_the_count_and_carries_on(self):
        engine = Engine(SCRIPT)
        giant = Giant(engine)
        giant.run(61)
        # Variables pass to the winner; modifiers and lists do not, and the system keeps neither.
        winner = Country("USA")
        winner.vars, winner.queue = dict(giant.country.vars), giant.country.queue
        for building in giant.home:
            building.state.owner = winner
        giant.country = winner
        giant.run(60)
        self.assertTrue(giant.on())
        self.assertLess(max(engine.decisions["USA"][-4:]), constant("te_bi_reserve") + 60)


class TheGeneratedFiles(unittest.TestCase):
    def test_they_are_current(self):
        self.assertEqual(gen.regenerate(dry_run=True), [],
                         "run .venv/bin/python scripts/generators/gen_batch_investment.py")

    def test_one_bom_each(self):
        for path in (GENERATED_EFFECTS, GENERATED_TRIGGERS, EFFECTS, TRIGGERS, VALUES, ON_ACTIONS):
            data = path.read_bytes()
            self.assertTrue(data.startswith(b"\xef\xbb\xbf") and not data[3:].startswith(b"\xef\xbb\xbf"), path.name)

    def branches(self):
        return [limit[0][2] for _, _, body in SCRIPT.effects["te_bi_queue_batch"]
                for key, _, limit in body if key == "limit"]

    def test_every_branch_hands_the_state_its_own_building(self):
        for _, _, body in SCRIPT.effects["te_bi_queue_batch"]:
            fields = dict((k, v) for k, _, v in body)
            kind = fields["limit"][0][2]
            self.assertEqual(fields["limit"], [("is_building_type", "=", kind)])
            self.assertEqual(fields["state"], [("te_bi_queue_in_state", "=", [("B", "=", kind)])])

    def test_the_branches_form_one_chain(self):
        keys = [key for key, _, _ in SCRIPT.effects["te_bi_queue_batch"]]
        self.assertEqual(keys, ["if"] + ["else_if"] * (len(keys) - 1))

    def test_the_buildings_investors_place_by_the_thousand_have_a_branch(self):
        # The 2050 report's list (finding 1), and every building the old, unused bulk pass named.
        branches = set(self.branches())
        old = {value for key, _, block in read(OLD_LIST) if key == "is_privately_expandable_building_type"
               for _, _, group in block for _, _, value in group}
        self.assertGreater(len(old), 30)
        self.assertEqual(old - branches, set())
        for kind in INDUSTRIES + LOCAL:
            self.assertIn(kind, branches)

    def test_no_government_or_company_building_has_one(self):
        branches = set(self.branches())
        for kind in ("building_government_administration", "building_barrack", "building_university",
                     "te_construction_market_site", "building_airbus_lagardere_plant", "building_urban_center",
                     "building_financial_district", "building_subsistence_farm"):
            self.assertNotIn(kind, branches)

    def test_the_local_goods_list(self):
        state = gen.load_state()
        self.assertEqual(gen.local_goods(state), ["digital_access", "electricity", "services", "transportation"])
        listed = {value for _, _, group in SCRIPT.triggers["te_bi_local_goods_building"] for _, _, value in group}
        self.assertLessEqual(listed, set(self.branches()))
        for kind in ("building_railway", "building_network_infrastructure", "building_power_plant"):
            self.assertIn(kind, listed)
        for kind in ("building_steel_mill", "building_art_academy", "building_wheat_farm"):
            self.assertNotIn(kind, listed)


class TheWiring(unittest.TestCase):
    def test_the_hook_and_the_pulse_are_registered(self):
        self.assertEqual(SCRIPT.on_actions["on_start_expanding_building"],
                         [("on_actions", "=", [("te_bi_on_start_expanding", None, None)])])
        self.assertEqual(SCRIPT.on_actions["on_monthly_pulse_country"],
                         [("on_actions", "=", [("te_bi_monthly_on_action", None, None)])])

    def test_an_unwatched_country_costs_the_hook_one_variable_test(self):
        trigger = dict((k, v) for k, _, v in SCRIPT.on_actions["te_bi_on_start_expanding"])["trigger"]
        self.assertEqual(trigger, [("owner", "?=", [("has_variable", "=", "te_bi_watch")])])

    def test_every_variable_the_hook_reads_is_set_when_watching_starts_and_removed_when_it_ends(self):
        text = EFFECTS.read_text(encoding="utf-8-sig")
        used = set(re.findall(r"\bvar:(te_bi_\w+)", text)) | set(re.findall(r"Var\('(te_bi_\w+)'\)", text))
        engine = Engine(SCRIPT)
        country = Country("AAA")
        Run(engine, country).effect(SCRIPT.effects["te_bi_watch_start"], country)
        self.assertEqual(used - set(country.vars), set())
        country.vars["te_bi_on"] = (True, None)
        Run(engine, country).effect(SCRIPT.effects["te_bi_clear"], country)
        self.assertEqual(country.vars, {})

    def test_every_log_value_has_its_wrapper(self):
        text = EFFECTS.read_text(encoding="utf-8-sig")
        for name in set(re.findall(r"ScriptValue\('(\w+)'\)", text)):
            self.assertIn(name, SCRIPT.values, name)
        for name in set(re.findall(r"name = (te_bi_log_\w+)", text)):
            self.assertIn(f"{name}_g", SCRIPT.values, name)

    def test_the_mark_lasts_less_than_a_week(self):
        mark = dict((k, v) for k, _, v in SCRIPT.effects["te_bi_queue_in_state"][1][2])["set_variable"]
        self.assertEqual(mark, [("name", "=", "te_bi_m_$B$"), ("days", "=", "6")])


if __name__ == "__main__":
    unittest.main()
