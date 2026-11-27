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
        self.pending = 0  # its levels in any queue
        state.buildings[kind] = self


class Engine:
    """The engine as far as the script meets it. The keyword arguments are the assumptions the script rests on; each
    default is the assumed behavior."""

    LIMIT = 1000

    def __init__(self, script, *, hook="inside", script_hook=None, count_first=True, recheck=True, refuse=None,
                 answer=0, rules=(), limit=LIMIT):
        self.script = script
        self.limit = limit  # where the pass stops queueing for a country
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
        self.calls = 0  # on-action calls made with no effect running: each is one pick's hook
        self.flushing = False
        self.decisions = {}  # tag -> the engine's decisions in each weekly pass

    # -- queueing ---------------------------------------------------------------------------------------------------
    def queue_private(self, investor, building, who):
        mode = self.script_hook if who == "script" else self.hook

        def count():
            investor.queue.append((building, who))
            building.pending += 1

        if self.count_first:
            count()
            self.fire(building, mode)
        else:
            self.fire(building, mode)
            count()

    def queue_government(self, building):
        building.state.owner.government_queue += 1
        building.pending += 1
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
        if self.depth == 0:
            self.calls += 1
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
        if building.room is not None and building.pending >= building.room:
            return
        self.queue_private(state.owner, building, "script")
        for _ in range(self.answer):
            state.owner.queue.append((building, "answer"))
            building.pending += 1

    # -- the week ---------------------------------------------------------------------------------------------------
    def finish(self, country, levels):
        done, country.queue = country.queue[:levels], country.queue[levels:]
        for building, _ in done:
            building.level += 1
            building.pending -= 1

    def invest(self, country, pick, updates=5000):
        """The weekly pass: one level a decision, until the queue is full."""
        decisions = 0
        slots = self.limit - len(country.queue)
        for _ in range(updates):
            if self.recheck and len(country.queue) >= self.limit:
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
        if raw == "level_after_queued_constructions" and isinstance(scope, Building):
            return float(scope.level + scope.pending)
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
            return scope.room is None or scope.pending + self.value(val, scope) <= scope.room
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
# Very large economies: forty states of city industries, a railway and a power plant in each, and investment abroad.
# ---------------------------------------------------------------------------------------------------------------------
INDUSTRIES = ("building_steel_mill", "building_motor_industry", "building_tooling_workshop", "building_glassworks",
              "building_electrics_industry", "building_chemical_plant", "building_art_academy",
              "building_textile_mill")
LOCAL = ("building_railway", "building_power_plant")


class Investor:
    """A country, its buildings and where its investors place their levels."""

    def __init__(self, tag, *, states, levels, seed, kinds=INDUSTRIES + LOCAL):
        self.random = random.Random(seed)
        self.country = Country(tag)
        self.buildings = []
        for index in range(states):
            state = State(f"{tag}{index}", self.country)
            for kind in kinds:
                self.buildings.append(Building(kind, state, self.random.randint(*levels)))
        self.abroad, self.share_abroad = [], 0.0
        self.favourites, self.share_favourites = [], 0.0

    def invests_in(self, other, share):
        self.abroad, self.share_abroad = other.buildings, share

    def favours(self, count, share):
        """`share` of the picks at home go to the `count` largest buildings: the engine picks its best candidates
        over and over."""
        self.favourites = sorted(self.buildings, key=lambda b: -b.level)[:count]
        self.share_favourites = share

    def pick(self):
        if self.random.random() < self.share_abroad:
            return self.random.choice(self.abroad)
        if self.favourites and self.random.random() < self.share_favourites:
            return self.random.choice(self.favourites)
        return self.random.choice(self.buildings)

    def fill(self, levels=Engine.LIMIT):
        """The queue as the engine left it last week."""
        while len(self.country.queue) < levels:
            building = self.pick()
            self.country.queue.append((building, "engine"))
            building.pending += 1


class Giant:
    """The USA, investing three levels in ten abroad, in a host that is small unless `rival`: then the host is a
    second very large economy whose investors place three in ten of their levels in the USA."""

    def __init__(self, engine, *, abroad=0.3, rival=False, queued=Engine.LIMIT):
        self.engine = engine
        self.usa = Investor("USA", states=40, levels=(200, 5000), seed=7)
        if rival:
            self.other = Investor("MEX", states=40, levels=(200, 5000), seed=11)
            self.other.invests_in(self.usa, 0.3)
        else:
            self.other = Investor("MEX", states=10, levels=(50, 500), seed=11, kinds=INDUSTRIES)
        self.usa.invests_in(self.other, abroad)
        self.rival = rival
        self.usa.fill(queued)
        if rival:
            self.other.fill()
        self.country, self.host = self.usa.country, self.other.country
        self.home, self.foreign = self.usa.buildings, self.other.buildings
        self.pick = self.usa.pick

    def investors(self):
        return [self.usa, self.other] if self.rival else [self.usa]

    def run(self, days, *, finish=1000, updates=5000):
        """Every seventh day the week's levels finish and the pass refills the queue; every thirtieth is a monthly
        pulse."""
        engine = self.engine
        for _ in range(days):
            if engine.day % 7 == 0:
                for investor in self.investors():
                    engine.finish(investor.country, finish)
                for investor in self.investors():
                    engine.invest(investor.country, investor.pick, updates)
            if engine.day % 30 == 0:
                engine.monthly(self.country)
                engine.monthly(self.host)
            engine.day += 1
            self.check()

    def check(self):
        """What holds on every day in every engine: a level script queued is in its own country, for its own
        country."""
        for investor in (self.usa, self.other):
            for building, who in investor.country.queue:
                if who == "script":
                    assert building.state.owner is investor.country, "script queued a level abroad"
        if not self.rival:
            assert not self.host.queue, "a level was queued for the host country"
            assert not self.host.vars, "the host country, never at 200 levels queued, is watched"

    def on(self):
        return "te_bi_on" in self.country.vars

    def var(self, name):
        return self.country.vars[name][0]


SCRIPT = Script()


def constant(name):
    """A tuning value, worked out where it is a sum of others."""
    country = Country("AAA")
    return Run(Engine(SCRIPT), country).value(name, country)


def verdicts(engine):
    """Each self-check's verdict lines, in order."""
    found = {}
    for line in engine.lines("TE_SELF_CHECK"):
        if " START " not in line:
            found.setdefault(line.split()[2], []).append(line.split()[1])
    return found


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
        self.assertFalse(self.engine.lines("TE_BI off"))

    def test_the_pass_makes_a_small_fraction_of_its_decisions(self):
        self.assertGreater(min(self.before), 900)
        # The reserve's hundred single levels, and a dozen or two batches.
        self.assertLess(max(self.after), constant("te_bi_reserve") + 60)
        self.assertLess(sum(self.after) / len(self.after), 0.15 * sum(self.before) / len(self.before))

    def test_the_queue_is_as_long_as_before(self):
        # Refilled to the engine's limit every week either way, so what reads the queue's length reads the same.
        self.assertEqual(len(self.giant.country.queue), Engine.LIMIT)
        self.assertEqual(self.giant.var("te_bi_maxq"), Engine.LIMIT)

    def test_every_self_check_reads_ok(self):
        self.assertEqual(verdicts(self.engine), {"batch_invest_hook": ["OK"], "batch_invest_month": ["OK"],
                                                 "batch_invest_queue": ["OK"], "batch_invest_reentry": ["OK"]})
        self.assertNotIn("te_bi_tripped", self.engine.globals)

    def test_each_verdict_follows_its_start_line(self):
        log = self.engine.log
        for name, verdict in (("batch_invest_queue", "batch_invest_queue"), ("batch_invest_hook", "batch_invest_hook"),
                              ("batch_invest_month", "batch_invest_month")):
            starts = [i for i, line in enumerate(log) if line.startswith(f"TE_SELF_CHECK START {name}")]
            self.assertEqual(len(starts), 1, name)
            self.assertIn(f" {verdict} ", log[starts[0] + 1])

    def test_the_first_batchs_start_line_comes_before_the_batch(self):
        # A crash at the first level queued from inside the hook leaves this line the last of its kind.
        start = self.engine.lines("TE_SELF_CHECK START batch_invest_queue")[0]
        self.assertRegex(start, r"asked=\d+ ")
        self.assertNotIn("asked=-1", start)

    def test_the_month_line_prints_each_of_the_first_months(self):
        lines = self.engine.lines("TE_BI month country=USA")
        self.assertEqual(len(lines), 3)  # days 60, 90, 120
        figures = dict(part.split("=") for part in lines[-1].split()[2:])
        for name in ("over", "short", "unknown", "capped"):
            self.assertEqual(figures[name], "0", name)
        self.assertGreater(int(figures["added"]), 3000)
        self.assertLess(int(figures["picks_home"]) + int(figures["picks_other"]), 800)
        # The reserve's single levels at home are the picks that found no room.
        self.assertGreater(int(figures["noroom"]), 100)


class WhatABatchIs(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(SCRIPT)
        self.giant = Giant(self.engine)
        self.queued, self.most_pending = [], {}
        original = self.engine.script_queues

        def spy(state, kind):
            building = state.buildings[kind]
            self.queued.append((self.engine.day, building, len(state.owner.queue), self.engine.calls))
            original(state, kind)
            self.most_pending[building] = max(self.most_pending.get(building, 0), building.pending / building.level)

        self.engine.script_queues = spy

    def batches(self):
        """The levels each pick's hook queued."""
        grouped = {}
        for _, building, _, call in self.queued:
            grouped.setdefault((call, building), []).append(building)
        return grouped

    def test_no_batch_is_queued_before_batching_is_on(self):
        self.giant.run(100)
        self.assertTrue(self.queued)
        self.assertGreaterEqual(min(day for day, _, _, _ in self.queued), 30)

    def test_no_level_is_queued_at_or_past_the_ceiling(self):
        self.giant.run(100)
        self.assertLess(max(length for _, _, length, _ in self.queued), constant("te_bi_ceiling"))

    def test_a_pick_stands_for_a_hundred_levels_at_most_and_ten_for_a_local_good(self):
        self.giant.run(100)
        sizes = set()
        for (_, building), levels in self.batches().items():
            total = len(levels) + 1  # the engine's own level
            local = building.kind in LOCAL
            self.assertLessEqual(total, constant("te_bi_local_batch_max" if local else "te_bi_batch_max"))
            sizes.add((local, total))
        # Both caps are reached by the largest buildings.
        self.assertIn((False, int(constant("te_bi_batch_max"))), sizes)
        self.assertIn((True, int(constant("te_bi_local_batch_max"))), sizes)

    def test_no_building_has_more_than_a_tenth_of_its_size_queued(self):
        self.giant.usa.favours(10, 0.8)
        self.giant.run(100)
        for building, share in self.most_pending.items():
            local = building.kind in LOCAL
            self.assertLessEqual(share, constant("te_bi_local_share" if local else "te_bi_share"), building.kind)
        # A favourite is picked many times in a pass, and takes more than one batch.
        self.assertGreater(max(self.most_pending.values()), 0.05)

    def test_slow_levels_do_not_stack_batch_on_batch(self):
        # Three levels in ten finish a week, so a level waits three weeks and more: a building picked again while
        # its batch is still queued gets no second one.
        self.giant.run(160, finish=300)
        self.assertTrue(self.giant.on())
        self.assertTrue(self.queued)
        self.assertLessEqual(max(self.most_pending.values()), constant("te_bi_share"))


class TheSizes(unittest.TestCase):
    def size(self, kind, level, pending=1):
        engine = Engine(SCRIPT)
        building = Building(kind, State("s", Country("AAA")), level)
        building.pending = pending  # the engine's own level, just queued
        return Run(engine, building).value("te_bi_batch_extra", building)

    def test_an_ordinary_building(self):
        self.assertEqual([self.size("building_steel_mill", level) for level in (0, 19, 20, 29, 30, 555, 999, 1000, 9000)],
                         [0, 0, 1, 1, 2, 54, 98, 99, 99])

    def test_a_local_goods_building(self):
        self.assertEqual([self.size("building_railway", level) for level in (0, 99, 100, 149, 150, 499, 500, 9000)],
                         [0, 0, 1, 1, 2, 8, 9, 9])

    def test_what_is_queued_already_comes_off(self):
        self.assertEqual([self.size("building_steel_mill", 1000, pending) for pending in (1, 40, 99, 100, 250)],
                         [99, 60, 1, 0, 0])

    def test_a_large_building_takes_a_hundred_a_pick_until_a_tenth_is_queued(self):
        # The first batch in game was for a building of 6,579 levels (2026-11-27).
        self.assertEqual([self.size("building_steel_mill", 6579, pending) for pending in (1, 100, 500, 600, 657, 700)],
                         [99, 99, 99, 57, 0, 0])
        self.assertEqual([self.size("building_railway", 3000, pending) for pending in (1, 10, 55, 60)], [9, 9, 5, 0])

    def test_the_tuning_is_in_order(self):
        self.assertLess(constant("te_bi_off_levels"), constant("te_bi_on_levels"))
        self.assertLess(constant("te_bi_unwatch_queue"), constant("te_bi_watch_queue"))
        self.assertLess(constant("te_bi_local_share"), constant("te_bi_share"))
        self.assertLess(constant("te_bi_local_batch_max"), constant("te_bi_batch_max"))
        # A batch's own levels come back through the hook inside one `while`, which the engine stops at 1,000 passes.
        self.assertLess(constant("te_bi_batch_max"), 1000)
        # A country placing te_bi_on_levels a month holds a week's worth in its queue, so it is watched by then.
        self.assertLessEqual(constant("te_bi_watch_queue"), constant("te_bi_on_levels") / 4)
        # The engine's own single levels are how script sees it reach its limit: they must start under "near".
        self.assertLess(constant("te_bi_ceiling"), constant("te_bi_engine_queue_near"))
        self.assertEqual(constant("te_bi_ceiling"), 900)

    def test_the_mod_leaves_the_engines_limit_alone(self):
        # The values file names NAI's CONSTRUCTION_MAX_NUM_PRODUCTION_BUILDING_CONSTRUCTIONS defines (1 + at most
        # 999) as the likely source of the engine's 1,000. Script cannot read a define: if the mod ever sets one of
        # them, te_bi_engine_queue has to follow.
        for path in sorted((ROOT / "common" / "defines").glob("*.txt")):
            self.assertNotIn("CONSTRUCTION_MAX_NUM_PRODUCTION_BUILDING_CONSTRUCTIONS",
                             path.read_text(encoding="utf-8-sig"), path.name)
        self.assertEqual(constant("te_bi_engine_queue"), 1 + 999)


class AnEngineWithFavourites(unittest.TestCase):
    """What the first run in game showed (2026-11-27, the USA of 2050): the engine picks its best few buildings over
    and over within a pass. With a hundred as the most a building could have queued, 315 of 597 picks were single
    levels of buildings that already held their hundred."""

    def run_with(self, script):
        engine = Engine(script)
        giant = Giant(engine)
        giant.usa.favours(3, 0.95)
        giant.run(120)
        self.assertTrue(giant.on())
        month = dict(part.split("=") for part in engine.lines("TE_BI month")[-1].split()[2:])
        return engine.decisions["USA"][9:], int(month["small"]), int(month["batches"])

    def test_the_pass_still_fills_the_queue_in_few_decisions(self):
        decisions, small, batches = self.run_with(SCRIPT)
        self.assertLess(max(decisions), constant("te_bi_reserve") + 60)
        # Few picks are turned away as small: only those of a favourite with its tenth queued.
        self.assertLess(small, batches)

    def test_the_model_shows_what_the_game_showed_under_the_first_rule(self):
        # The rule as first run in game: a hundred was also the most a building could have queued. The game's two
        # passes took about 240 and 365 decisions; this holds the model to the same failure, so the test above means
        # something.
        first = Script()
        first.values["te_bi_batch_extra"], _ = parse_block(tokenize("""
            value = level
            if = { limit = { te_bi_local_goods_building = yes } multiply = te_bi_local_share max = te_bi_local_batch_max }
            else = { multiply = te_bi_share max = te_bi_batch_max }
            floor = yes
            add = level
            subtract = level_after_queued_constructions
            min = 0"""))
        decisions, small, batches = self.run_with(first)
        self.assertGreater(min(decisions), constant("te_bi_reserve") + 60)
        self.assertGreater(small, 5 * batches)


class ASmallReserve(unittest.TestCase):
    def test_the_pass_is_left_a_few_dozen_decisions(self):
        script = Script()
        script.values["te_bi_reserve"] = "20"
        engine = Engine(script)
        giant = Giant(engine)
        giant.run(120)
        self.assertTrue(giant.on())
        self.assertLess(max(engine.decisions["USA"][9:]), 20 + 60)
        self.assertEqual(len(giant.country.queue), Engine.LIMIT)


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
        target = next(b for b in self.giant.home if b.kind == "building_steel_mill" and not b.pending)
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

    def test_a_new_building_keeps_its_single_level(self):
        new = Building("building_paper_mill", self.giant.home[0].state, 0)
        self.engine.finish(self.giant.country, 500)
        self.engine.queue_government(self.giant.home[1])
        before, small = len(self.giant.country.queue), self.giant.var("te_bi_small")
        self.engine.queue_private(self.giant.country, new, "engine")
        self.assertEqual(len(self.giant.country.queue), before + 1)
        self.assertEqual(self.giant.var("te_bi_small"), small + 1)

    def test_a_building_with_no_branch_is_counted_unknown(self):
        odd = Building("building_from_another_mod", self.giant.home[0].state, 900)
        self.engine.finish(self.giant.country, 500)
        self.engine.queue_government(self.giant.home[1])
        before, unknown = len(self.giant.country.queue), self.giant.var("te_bi_unknown")
        self.engine.queue_private(self.giant.country, odd, "engine")
        self.assertEqual(len(self.giant.country.queue), before + 1)
        self.assertEqual(self.giant.var("te_bi_unknown"), unknown + 1)
        self.assertNotIn("te_bi_placing", self.engine.globals)


class TwoGiants(unittest.TestCase):
    """Two very large economies, each placing three levels in ten in the other."""

    @classmethod
    def setUpClass(cls):
        cls.engine = Engine(SCRIPT)
        cls.giant = Giant(cls.engine, rival=True)
        cls.giant.run(150)

    def test_both_batch(self):
        self.assertEqual(len(self.engine.lines("TE_BI on country=")), 2)
        for tag in ("USA", "MEX"):
            self.assertLess(max(self.engine.decisions[tag][9:]), constant("te_bi_reserve") + 60, tag)

    def test_neither_queue_passes_the_limit_and_nothing_trips(self):
        for country in (self.giant.country, self.giant.host):
            self.assertLessEqual(len(country.queue), Engine.LIMIT)
            self.assertLessEqual(country.vars["te_bi_maxq"][0], Engine.LIMIT)
        self.assertNotIn("te_bi_tripped", self.engine.globals)
        self.assertFalse(self.engine.lines("TE_SELF_CHECK BROKEN"))

    def test_each_still_places_levels_in_the_other(self):
        for country in (self.giant.country, self.giant.host):
            abroad = sum(1 for building, _ in country.queue if building.state.owner is not country)
            self.assertGreater(abroad, 10)


class OnlyAtTheEnginesLimit(unittest.TestCase):
    """Batches change which levels are queued, not how many, only where the engine itself fills the queue to its
    limit. A country held under it must not batch, or its queue would grow."""

    def test_a_pass_short_of_updates_never_batches(self):
        # 300 decisions a week, and everything finishes: the queue holds 300.
        engine = Engine(SCRIPT)
        giant = Giant(engine, queued=300)
        giant.run(150, updates=300)
        self.assertGreaterEqual(giant.var("te_bi_home"), 0)  # watched
        self.assertFalse(engine.lines("TE_BI on"))
        self.assertLessEqual(len(giant.country.queue), 300)
        self.assertTrue(all(decisions == 300 for decisions in engine.decisions["USA"]))

    def test_a_country_whose_own_limit_is_lower_never_batches(self):
        # The limit follows the construction a country makes; this one's is 600.
        engine = Engine(SCRIPT, limit=600)
        giant = Giant(engine, queued=600)
        giant.run(150)
        self.assertFalse(engine.lines("TE_BI on"))
        self.assertLessEqual(len(giant.country.queue), 600)

    def test_a_batching_country_whose_limit_falls_stops_within_a_month(self):
        engine = Engine(SCRIPT)
        giant = Giant(engine)
        giant.run(61)
        self.assertTrue(giant.on())
        engine.limit = 600
        giant.run(60)
        self.assertFalse(giant.on())
        self.assertEqual(len(engine.lines("TE_BI off country=USA")), 1)
        self.assertLessEqual(len(giant.country.queue), 600)
        self.assertNotIn("te_bi_tripped", engine.globals)

    def test_investors_who_build_mostly_abroad_do_not_batch(self):
        # 1,000 levels a week, 900 of them abroad: about 400 a month at home.
        engine = Engine(SCRIPT)
        giant = Giant(engine, abroad=0.9)
        giant.run(150)
        self.assertFalse(engine.lines("TE_BI on"))
        self.assertTrue(all(decisions == 1000 for decisions in engine.decisions["USA"]))


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
        giant = Giant(engine, queued=150)
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

    def test_off_and_on_again_re_arms_a_trip(self):
        engine = Engine(SCRIPT)
        giant = Giant(engine)
        giant.run(61)
        engine.globals["te_bi_tripped"] = True
        giant.run(30)
        self.assertFalse(giant.on())
        engine.rules.add("te_batch_investment_disabled")
        giant.run(30)
        self.assertNotIn("te_bi_tripped", engine.globals)
        engine.rules.clear()
        giant.run(90)
        self.assertTrue(giant.on())

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

    def test_the_hook_runs_after_the_pass(self):
        engine = Engine(SCRIPT, hook="after")
        giant = Giant(engine)
        giant.run(300)
        self.assertFalse(giant.on())
        self.assertEqual(verdicts(engine), {"batch_invest_hook": ["BROKEN"]})  # once, at the sixth month
        self.assertTrue(all(decisions == 1000 for decisions in engine.decisions["USA"][1:]))

    def test_the_hook_never_runs_for_a_private_level(self):
        engine = Engine(SCRIPT, hook="never")
        giant = Giant(engine)
        giant.run(240)
        self.assertFalse(giant.on())
        self.assertEqual(verdicts(engine), {"batch_invest_hook": ["BROKEN"]})

    def test_a_small_countrys_ok_does_not_hide_a_giant_the_hook_cannot_see(self):
        # The hook's OK prints once a game, from whichever country shows it first; its BROKEN is each country's own.
        engine = Engine(SCRIPT, hook="after")
        giant = Giant(engine)
        engine.globals["te_bi_checked_hook"] = True
        giant.run(240)
        self.assertEqual(verdicts(engine), {"batch_invest_hook": ["BROKEN"]})

    def test_a_stalled_full_queue_is_not_called_broken(self):
        engine = Engine(SCRIPT, hook="never")
        giant = Giant(engine)
        giant.country.gross_income = giant.country.net_income = 0.0  # the pool pays for nothing
        giant.run(240, finish=0)
        self.assertEqual(verdicts(engine), {})

    def test_the_pass_does_not_read_the_queue_again(self):
        engine = Engine(SCRIPT, recheck=False)
        giant = Giant(engine)
        giant.run(150)
        # The first batching pass overshoots, once: the first pick past the limit trips batching for good.
        self.assertEqual(verdicts(engine)["batch_invest_limit"], ["BROKEN"])
        self.assertIn("te_bi_tripped", engine.globals)
        self.assertIn("day35", engine.lines("TE_SELF_CHECK BROKEN batch_invest_limit")[0])
        self.assertFalse(giant.on())
        self.assertEqual(len(engine.lines("TE_BI on")), 1)
        self.assertEqual(verdicts(engine)["batch_invest_month"], ["BROKEN"])
        # One pass's worth too many, built off in the next weeks; then the queue is the engine's again.
        self.assertLessEqual(max(engine.decisions["USA"]), Engine.LIMIT)
        self.assertEqual(len(giant.country.queue), Engine.LIMIT)
        self.assertTrue(all(decisions == 1000 for decisions in engine.decisions["USA"][8:]))

    def test_the_hook_runs_before_the_level_is_counted(self):
        engine = Engine(SCRIPT, count_first=False)
        giant = Giant(engine)
        giant.run(120)
        self.assertEqual(verdicts(engine).get("batch_invest_reentry"), ["BROKEN"])
        self.assertLessEqual(len(giant.country.queue), Engine.LIMIT)
        self.assertNotIn("te_bi_tripped", engine.globals)

    def test_scripts_own_levels_reach_the_hook_later(self):
        engine = Engine(SCRIPT, script_hook="after")
        giant = Giant(engine)
        giant.run(120)
        found = verdicts(engine)
        self.assertEqual(found["batch_invest_reentry"], ["NO_VERDICT"])
        self.assertEqual(found["batch_invest_queue"], ["OK"])
        self.assertEqual(found["batch_invest_month"], ["OK"])
        # The late calls find the queue as the batch left it, and batch nothing.
        self.assertLessEqual(len(giant.country.queue), Engine.LIMIT)
        self.assertLess(max(engine.decisions["USA"][9:]), constant("te_bi_reserve") + 60)

    def test_the_effect_queues_nothing_from_the_hook(self):
        engine = Engine(SCRIPT, refuse=lambda building: True)
        giant = Giant(engine)
        giant.run(120)
        found = verdicts(engine)
        self.assertEqual(found["batch_invest_queue"], ["BROKEN"])
        self.assertIn("queued=0", engine.lines("TE_SELF_CHECK BROKEN batch_invest_queue")[0])
        self.assertEqual(found["batch_invest_month"], ["BROKEN"])
        self.assertIn("added=0", engine.lines("TE_SELF_CHECK BROKEN batch_invest_month")[0])
        self.assertTrue(all(decisions >= 999 for decisions in engine.decisions["USA"][1:]))

    def test_the_effect_refuses_most_levels(self):
        refused = iter(range(10 ** 9))
        engine = Engine(SCRIPT, refuse=lambda building: next(refused) % 3 != 0)
        giant = Giant(engine)
        giant.run(120)
        self.assertEqual(verdicts(engine)["batch_invest_month"], ["BROKEN"])

    def test_levels_queued_in_answer_to_a_batch_trip_it_for_good(self):
        engine = Engine(SCRIPT, answer=1)
        giant = Giant(engine)
        giant.run(120)
        self.assertEqual(len(engine.lines("TE_SELF_CHECK BROKEN batch_invest_runaway")), 1)
        self.assertIn("te_bi_tripped", engine.globals)
        self.assertFalse(giant.on())
        # One batch, twice its size, and no more.
        self.assertEqual(sum(1 for _, who in giant.country.queue if who in ("script", "answer")), 0)
        self.assertLessEqual(len(giant.country.queue), Engine.LIMIT)
        self.assertEqual(len(engine.lines("TE_BI on")), 1)
        self.assertTrue(all(decisions >= 999 for decisions in engine.decisions["USA"][7:]))

    def test_a_flag_left_up_is_cleared_and_reported(self):
        engine = Engine(SCRIPT)
        giant = Giant(engine)
        giant.run(61)
        engine.globals["te_bi_placing"] = 0.0
        engine.finish(giant.country, 800)
        self.assertEqual(engine.invest(giant.country, giant.pick), 800)  # every level passed over
        engine.monthly(giant.country)
        self.assertNotIn("te_bi_placing", engine.globals)
        self.assertNotIn("te_bi_nested_queue", engine.globals)
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
        giant.country = giant.usa.country = winner
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
        # The 2050 report's list (finding 1), and every building the old, unused bulk pass named but the one
        # the generator leaves out on purpose.
        branches = set(self.branches())
        old = {value for key, _, block in read(OLD_LIST) if key == "is_privately_expandable_building_type"
               for _, _, group in block for _, _, value in group}
        self.assertGreater(len(old), 30)
        self.assertEqual(old - branches, {"building_space_mine", "building_space_resort"} & old)
        self.assertLessEqual(old - branches, set(gen.EXCLUDED))
        for kind in INDUSTRIES + LOCAL:
            self.assertIn(kind, branches)

    def test_no_government_or_company_building_has_one(self):
        branches = set(self.branches())
        for kind in ("building_government_administration", "building_barrack", "building_university",
                     "te_construction_market_site", "building_airbus_lagardere_plant", "building_urban_center",
                     "building_financial_district", "building_subsistence_farm"):
            self.assertNotIn(kind, branches)

    def test_a_building_whose_private_gate_counts_levels_has_none(self):
        # A batch could overrun a gate that counts queued levels; can_queue_building_levels does not read it.
        branches = set(self.branches())
        self.assertEqual(set(gen.EXCLUDED), {"building_space_mine", "building_space_resort", "building_trade_center"})
        self.assertFalse(set(gen.EXCLUDED) & branches)

    def test_every_other_private_gate_has_been_read(self):
        state = gen.load_state()
        buildings = state.get_data("Buildings")
        gated = {name for name in self.branches() if "can_build_private" in gen.body_of(buildings, name)}
        self.assertEqual(gated, set(gen.GATES_READ))

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
        text = EFFECTS.read_text(encoding="utf-8-sig") + VALUES.read_text(encoding="utf-8-sig")
        used = set(re.findall(r"\bvar:(te_bi_\w+)", text)) | set(re.findall(r"Var\('(te_bi_\w+)'\)", text))
        changed = set(re.findall(r"change_variable = \{ name = (te_bi_\w+)", text))
        engine = Engine(SCRIPT)
        country = Country("AAA")
        Run(engine, country).effect(SCRIPT.effects["te_bi_watch_start"], country)
        self.assertEqual((used | changed) - set(country.vars), set())
        country.vars["te_bi_on"] = (True, None)
        Run(engine, country).effect(SCRIPT.effects["te_bi_clear"], country)
        self.assertEqual(country.vars, {})

    def test_every_log_value_has_its_wrapper(self):
        text = EFFECTS.read_text(encoding="utf-8-sig")
        for name in set(re.findall(r"ScriptValue\('(\w+)'\)", text)):
            self.assertIn(name, SCRIPT.values, name)
        for name in set(re.findall(r"name = (te_bi_log_\w+)", text)):
            self.assertIn(f"{name}_g", SCRIPT.values, name)

    def test_no_state_or_building_holds_a_variable(self):
        # A building has no variable store, and the system needs none on a state: every variable is the country's.
        for name in ("te_bi_queue_in_state", "te_bi_try_batch", "te_bi_place", "te_bi_hook"):
            flat = repr(SCRIPT.effects[name])
            outside_owner = re.sub(r"\('owner', '=', \[.*?\]\)\]\)", "", flat)
            self.assertNotIn("'set_variable'", outside_owner, name)
            self.assertNotIn("'change_variable'", outside_owner, name)


if __name__ == "__main__":
    unittest.main()
