"""The assimilation cultures' yearly pass: who is taken, what each pop becomes, and the shape of the walk.

Design: docs/superpowers/specs/2026-11-25-assimilation-cultures-design.md, § The pass and § The rule; the plan's
Task 5 holds the names. Once a year, from each country's own pulse and under every setting of the rule, the pass
walks the country's incorporated states where a culture of another heritage group lives. In each it picks the host,
the owner's primary culture with the most people there (the capital's host where none lives there, worked out once a
pass), and walks the pops it takes: a culture that shares no heritage group with any primary culture, outside its
homeland unless the state allows that, at an acceptance status the owner's laws let assimilate. What a taken pop
becomes is the outcome table, where "local" is the state's local culture for the pop's heritage group, "targets" the
host language's hybrids, "cross" the owner's crossing share and "blocked" Ancestral Citizenship's bool:

    mode               speaks host  targets  local  becomes          fraction               not when
    1 Hybrid Cultures  no           any      > 0    te_hc_l_<group>  te_hc_pop_step         never
    1                  no           1        0      te_hc_t_<group>  te_hc_pop_step         never
    1                  no           0        0      te_hc_host       te_hc_pop_cross_step   blocked, slave, cross 0
    1                  yes          any      any    te_hc_host       te_hc_pop_cross_step   blocked, slave, cross 0
    2 Unrestricted     any          any      any    te_hc_host       te_hc_pop_step         blocked, slave
    3 None             any          any      any    te_hc_host       te_hc_pop_cross_step   blocked, slave, cross 0

and nothing converts in a state with no host. The local culture is found by trait in every state, so no culture is
named: one with people in the country, of the pop's heritage group, speaking the host's language, whose homeland is
this state or a state the owner holds that is also a primary culture's homeland.

The script can't run offline, so a small interpreter (`Interp`) runs it over a stub world of countries, states,
pops and cultures. It models if/else_if/else and trigger_if, limits with AND/OR/NOT/NOR/NAND, local variables,
saved scopes, the scope links and scope iterators the pass needs, script values, and scripted effects and triggers
with $ARG$ substitution, and it records each change_pop_culture. Anything else raises NotModeled naming it, so a
script that does something these tests don't model fails rather than passing untested; an error the interpreter can
see (a read of an unset local or of a scope never saved, a call whose arguments don't match its callee) raises
ScriptBug. Helpers other tasks own, or that are tested on their own, are stood in for where named: te_hcg_save_targets
(generated, Task 3) always, and te_hc_pick_host and te_hc_find_locals in the outcome table.

Run: python3 -m pytest test_assimilation_cultures_pass.py
"""

import math
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import assimilation_cultures_config as cfg  # noqa: E402
import vanilla_parsed  # noqa: E402

EFFECTS = ROOT / "common/scripted_effects/te_assimilation_culture_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_assimilation_culture_triggers.txt"
VALUES = ROOT / "common/script_values/te_assimilation_culture_values.txt"
ON_ACTIONS = ROOT / "common/on_actions/te_assimilation_culture_on_actions.txt"
PASS_FILES = (EFFECTS, TRIGGERS, VALUES, ON_ACTIONS)

GROUPS = tuple(group.key for group in cfg.GROUPS)
STATUSES = ("violent_hostility", "cultural_erasure", "open_prejudice", "second_rate_citizen", "full_acceptance")
# An acceptance well inside each status (vanilla's acceptance_status_2 to _5 are 20, 40, 60, 80).
ACCEPTANCE_IN = dict(zip(STATUSES, (10.0, 30.0, 50.0, 70.0, 90.0)))
SHARE = "country_cross_heritage_assimilation_add"
BLOCKED = "country_cross_heritage_assimilation_blocked_bool"
HOMELAND_BOOL = "state_allow_assimilation_in_homeland_bool"
STATE_MULT = "state_assimilation_mult"
STEP, CROSS_STEP = "te_hc_pop_step", "te_hc_pop_cross_step"
MODIFIERS = {
    "country": {SHARE, BLOCKED}
    | {f"country_allow_assimilation_{status}_bool" for status in STATUSES}
    | {f"country_assimilation_{status}_mult" for status in STATUSES},
    "state": {STATE_MULT, HOMELAND_BOOL},
}
RULE_WORDS = ("has_game_rule", "te_hc_mode_hybrid", "te_hc_mode_none", "local_var:te_hc_mode")
# Task 6's once-a-game self-checks (the house name is te_<system>_chk_*): run nowhere here. A call is recorded and
# skipped, and a global variable reads as set, so a check behind `NOT = { has_global_variable = ... }` stays shut.
SELF_CHECK = re.compile(r"^te_hc_(chk|self_?check)")


# ---------------------------------------------------------------------------------------------------------------
# Reading script
# ---------------------------------------------------------------------------------------------------------------

def read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def strip_comments(text):
    lines = []
    for line in text.splitlines():
        quoted = False
        for i, ch in enumerate(line):
            if ch == '"':
                quoted = not quoted
            elif ch == "#" and not quoted:
                line = line[:i]
                break
        lines.append(line)
    return "\n".join(lines)


def code(path):
    return strip_comments(read(path))


OPS = ("=", "?=", "!=", "<", "<=", ">", ">=", "==")
_TOKEN = re.compile(r'"(?:[^"\\\n]|\\.)*"|[{}]|\?=|!=|<=|>=|==|[=<>]|[^\s{}=<>!?"]+')


class Node:
    """One statement: `key op value`, `key op { children }`, or a bare word (op None)."""

    __slots__ = ("key", "op", "value", "children")

    def __init__(self, key, op=None, value=None, children=None):
        self.key, self.op, self.value, self.children = key, op, value, children

    def child(self, key):
        return next((c for c in self.children or () if c.key == key), None)

    def __repr__(self):
        if self.children is None:
            return " ".join(part for part in (self.key, self.op, self.value) if part)
        return f"{self.key} {self.op} {{ {' '.join(map(repr, self.children))} }}"


def parse(text):
    tokens = _TOKEN.findall(text)
    pos = 0

    def block(top):
        nonlocal pos
        nodes = []
        while pos < len(tokens):
            tok = tokens[pos]
            pos += 1
            if tok == "}":
                if top:
                    raise ValueError("an unbalanced }")
                return nodes
            if tok == "{":
                nodes.append(Node(None, None, None, block(False)))
            elif pos < len(tokens) and tokens[pos] in OPS:
                op = tokens[pos]
                pos += 1
                if pos >= len(tokens):
                    raise ValueError(f"{tok} {op} at the end of the text")
                if tokens[pos] == "{":
                    pos += 1
                    nodes.append(Node(tok, op, None, block(False)))
                else:
                    nodes.append(Node(tok, op, tokens[pos]))
                    pos += 1
            else:
                nodes.append(Node(tok))
        if not top:
            raise ValueError("an unclosed {")
        return nodes

    return block(True)


def top_level(path):
    """Each top-level `name = { ... }` or `name = value` of a script file: name -> ("block", body text) or
    ("scalar", value). A name defined twice fails: the engine keeps one and drops the other without a word."""
    text = code(path)
    toks = list(_TOKEN.finditer(text))
    defs, depth, i = {}, 0, 0
    while i < len(toks):
        tok = toks[i].group()
        if tok == "{":
            depth += 1
        elif tok == "}":
            depth -= 1
        elif depth == 0 and i + 2 < len(toks) and toks[i + 1].group() == "=":
            if tok in defs:
                raise ScriptBug(f"{Path(path).name}: {tok} is defined twice; the engine keeps only one")
            opening = toks[i + 2]
            if opening.group() == "{":
                level, j = 1, i + 3
                while level:
                    level += {"{": 1, "}": -1}.get(toks[j].group(), 0)
                    j += 1
                defs[tok] = ("block", text[opening.end():toks[j - 1].start()])
                i = j
                continue
            defs[tok] = ("scalar", opening.group())
            i += 3
            continue
        i += 1
    return defs


def words(text):
    return " ".join(text.split())


def body_text(path, name):
    form, text = top_level(path)[name]
    assert form == "block", name
    return text


def walk_nodes(nodes):
    for node in nodes:
        yield node
        if node.children:
            yield from walk_nodes(node.children)


# ---------------------------------------------------------------------------------------------------------------
# The interpreter
# ---------------------------------------------------------------------------------------------------------------

class NotModeled(Exception):
    """The script does something the interpreter does not model: extend the interpreter, or reconsider the script."""


class ScriptBug(AssertionError):
    """An error the engine would make of this script: a read of an unset local or of a scope never saved, a call
    whose arguments don't match its callee, a statement in the wrong scope."""


class Missing(Exception):
    """A saved scope or link that does not exist; `exists` reads it as false, anything else as a ScriptBug."""


_VANILLA_VALUES = None


def vanilla_values():
    """Vanilla's acceptance_status_1 to _5 (0, 20, 40, 60, 80), from the committed snapshot."""
    global _VANILLA_VALUES
    if _VANILLA_VALUES is None:
        snapshot = vanilla_parsed.load(str(ROOT / "vanilla_parsed")).data["Script Values"]
        _VANILLA_VALUES = {}
        for key, value in snapshot.items():
            if re.fullmatch(r"acceptance_status_\d", key):
                _VANILLA_VALUES[key] = float(value[1] if isinstance(value, (tuple, list)) else value)
    return _VANILLA_VALUES


def status_of(acceptance):
    thresholds = vanilla_values()
    status = STATUSES[0]
    for number, name in enumerate(STATUSES[1:], start=2):
        if acceptance >= thresholds[f"acceptance_status_{number}"]:
            status = name
    return status


class Script:
    """The pass's three script files (the on_action is read as text). Scripted bodies are parsed once per argument
    set, after $ARG$ substitution as the engine does it."""

    def __init__(self):
        self.effects = top_level(EFFECTS)
        self.triggers = top_level(TRIGGERS)
        self.values = top_level(VALUES)
        self._parsed = {}

    def body(self, kind, name, args=None):
        table = {"effect": self.effects, "trigger": self.triggers, "value": self.values}[kind]
        if name not in table:
            raise NotModeled(f"no scripted {kind} {name} in the pass's files (a stand-in may be missing)")
        form, text = table[name]
        if form != "block":
            raise NotModeled(f"the scripted {kind} {name} is not a block")
        args = args or {}
        key = (kind, name, tuple(sorted(args.items())))
        if key not in self._parsed:
            used, given = set(re.findall(r"\$(\w+)\$", text)), set(args)
            if used != given:
                raise ScriptBug(f"{name} uses ${'$, $'.join(sorted(used))}$ but the call passes {sorted(given)}")
            for arg, value in args.items():
                text = text.replace(f"${arg}$", value)
            self._parsed[key] = parse(text)
        return self._parsed[key]


class Ent:
    def __init__(self, eid, kind, **attrs):
        self.id, self.kind = eid, kind
        self.__dict__.update(attrs)

    def __repr__(self):
        return self.id


class World:
    """Countries, states, state regions, pops and cultures, by id. `mode` is the rule's setting (1 Hybrid Cultures,
    2 Unrestricted, 3 None), read only through the two mode triggers."""

    def __init__(self, mode=2):
        self.mode = mode
        self.ents = {}

    def add(self, eid, kind, **attrs):
        assert eid not in self.ents, eid
        self.ents[eid] = Ent(eid, kind, **attrs)
        return eid

    def culture(self, eid, group, language, heritage=None, homelands=(), fervor=0.0):
        return self.add(eid, "culture", group=group, language=language, heritage=heritage or f"heritage_{eid}",
                        homelands=set(homelands), fervor=fervor)

    def country(self, eid, primaries, capital=None, modifiers=None, cultures=None):
        return self.add(eid, "country", primaries=list(primaries), capital=capital, modifiers=dict(modifiers or {}),
                        cultures=cultures)

    def state(self, eid, owner, region=None, incorporated=True, modifiers=None, **facts):
        region = region or f"R_{eid}"
        if region not in self.ents:
            self.add(region, "region")
        return self.add(eid, "state", owner=owner, region=region, incorporated=incorporated,
                        modifiers=dict(modifiers or {}), pops=[], facts=facts)

    def pop(self, eid, state, culture, size=1000, acceptance=90.0, radicals=0.0, slave=False):
        self.ents[state].pops.append(eid)
        return self.add(eid, "pop", state=state, culture=culture, size=size, acceptance=acceptance,
                        radicals=radicals, slave=slave)

    def of_kind(self, kind):
        return [e for e in self.ents.values() if e.kind == kind]

    def link(self, eid, name):
        e = self.ents[eid]
        if name == "owner" and e.kind == "state":
            return e.owner
        if name == "owner" and e.kind == "pop":
            return self.ents[e.state].owner
        if name == "state" and e.kind == "pop":
            return e.state
        if name == "culture" and e.kind == "pop":
            return e.culture
        if name == "capital" and e.kind == "country":
            return e.capital
        if name == "state_region" and e.kind == "state":
            return e.region
        raise NotModeled(f"the link {name} from a {e.kind}")

    def state_cultures(self, sid):
        out = []
        for pid in self.ents[sid].pops:
            if self.ents[pid].culture not in out:
                out.append(self.ents[pid].culture)
        return out

    def country_cultures(self, cid):
        country = self.ents[cid]
        if country.cultures is not None:
            return list(country.cultures)
        out = []
        for state in self.of_kind("state"):
            if state.owner == cid:
                out += [c for c in self.state_cultures(state.id) if c not in out]
        return out

    def primary_homelands(self, cid):
        return set().union(*(self.ents[c].homelands for c in self.ents[cid].primaries))

    def items(self, eid, what):
        e = self.ents[eid]
        states = self.of_kind("state")
        if what == "scope_state" and e.kind == "country":
            return [s.id for s in states if s.owner == eid]
        if what == "scope_pop" and e.kind == "state":
            return list(e.pops)
        if what == "scope_pop" and e.kind == "culture":
            return [p.id for p in self.of_kind("pop") if p.culture == eid]
        if what == "scope_pop" and e.kind == "country":
            return [pid for s in states if s.owner == eid for pid in s.pops]
        if what == "scope_culture" and e.kind == "state":
            return self.state_cultures(eid)
        if what == "scope_culture" and e.kind == "country":
            return self.country_cultures(eid)
        if what == "primary_culture" and e.kind == "country":
            return list(e.primaries)
        if what == "scope_homeland_state" and e.kind == "culture":
            return [s.id for s in states if s.region in e.homelands]
        if what == "scope_homeland_state" and e.kind == "country":
            return [s.id for s in states if s.region in self.primary_homelands(eid)]
        raise NotModeled(f"the iterator over {what} from a {e.kind}")

    def modifier(self, eid, name):
        e = self.ents[eid]
        if name not in MODIFIERS.get(e.kind, ()):
            raise NotModeled(f"modifier:{name} read on a {e.kind}")
        return float(e.modifiers.get(name, 0.0))


LINKS = ("owner", "state", "culture", "capital", "state_region")
VALUE_READS = {"pop_radical_fraction": "pop", "total_size": "pop", "pop_acceptance": "pop",
               "culture_current_fervor": "culture"}
_ITERATOR = re.compile(r"^(every|random|ordered|any)_(scope_state|scope_pop|scope_culture|primary_culture"
                       r"|scope_homeland_state)$")
_COMPARE = {
    "=": lambda a, b: math.isclose(a, b, abs_tol=1e-9), "==": lambda a, b: math.isclose(a, b, abs_tol=1e-9),
    "?=": lambda a, b: math.isclose(a, b, abs_tol=1e-9), "!=": lambda a, b: not math.isclose(a, b, abs_tol=1e-9),
    "<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
}
_VALUE_OPS = {
    "value": lambda total, v: v, "add": lambda total, v: total + v, "subtract": lambda total, v: total - v,
    "multiply": lambda total, v: total * v, "min": lambda total, v: max(total, v),
    "max": lambda total, v: min(total, v),
}


def is_scope_path(token):
    return bool(token) and all(seg in LINKS or seg in ("this", "prev", "root") or seg.startswith("scope:")
                               for seg in token.split("."))


class Interp:
    """Runs scripted effects, triggers and values over a World. `stack` is the scope chain, the root first: `prev`
    is the scope before the current one, `root` the first. Stand-ins take (interp, stack, args)."""

    def __init__(self, script, world, effects=None, triggers=None, values=None, locals_=None, saved=None):
        self.script, self.world = script, world
        self.stand_in_effects = dict(effects or {})
        self.stand_in_triggers = {
            "te_hc_mode_hybrid": lambda i, stack, args: i.world.mode == 1,
            "te_hc_mode_none": lambda i, stack, args: i.world.mode == 3,
        }
        self.stand_in_triggers.update(triggers or {})
        self.value_overrides = dict(values or {})
        self.locals = dict(locals_ or {})
        self.saved = dict(saved or {})
        self.conversions = []   # (pop, target token, the scope it named, value token)
        self.calls = []         # (effect name, scope) for every te_hc_ or te_hcg_ effect run or stood in for
        self.walks = []         # (iterator, scope walked, effects running, scope stack)
        self.callstack = []
        self.after = {}         # effect name -> fn(interp, stack), run when that effect returns

    # -- entry points --

    def run_effect(self, name, stack, args=None):
        node = Node(name, "=", "yes") if not args else Node(name, "=", None, [Node(k, "=", v) for k, v in args.items()])
        self.call_effect(name, node, stack)

    def trigger(self, name, stack, args=None):
        node = Node(name, "=", "yes") if not args else Node(name, "=", None, [Node(k, "=", v) for k, v in args.items()])
        return self.call_trigger(name, node, stack)

    def value(self, name, stack):
        return self.read_value(name, stack)

    def ent(self, eid):
        return self.world.ents[eid]

    # -- effects --

    def run(self, nodes, stack):
        chain, taken = False, False
        for n in nodes:
            k = n.key
            if k in ("if", "else_if"):
                if n.children is None:
                    raise ScriptBug(f"{k} = {n.value}: not a block")
                if k == "if":
                    chain, taken = True, False
                elif not chain:
                    raise ScriptBug("an else_if with no if before it")
                if not taken:
                    limit = n.child("limit")
                    if limit is None:
                        raise NotModeled(f"an {k} with no limit")
                    if self.holds(limit.children, stack):
                        taken = True
                        self.run([c for c in n.children if c.key != "limit"], stack)
                continue
            if k == "else":
                if not chain:
                    raise ScriptBug("an else with no if before it")
                if not taken:
                    self.run(n.children, stack)
                chain = False
                continue
            chain = False
            self.effect(n, stack)

    def effect(self, n, stack):
        k, cur = n.key, stack[-1]
        if k is None or n.op is None:
            raise NotModeled(f"the bare {n!r} in an effect")
        if k == "limit":
            raise ScriptBug("a limit outside an if or an iterator")
        if k == "set_local_variable":
            if n.children is None or n.child("name") is None or n.child("value") is None:
                raise NotModeled(f"set_local_variable in a form other than {{ name = X value = Y }}: {n!r}")
            self.locals[n.child("name").value] = self.operand(n.child("value"), stack)
        elif k == "change_local_variable":
            name = n.child("name").value if n.children and n.child("name") else None
            if name is None:
                raise NotModeled(f"change_local_variable in a form other than {{ name = X add = Y }}: {n!r}")
            if name not in self.locals:
                raise ScriptBug(f"change_local_variable on the unset local {name}")
            for c in n.children:
                if c.key == "name":
                    continue
                if c.key not in ("add", "subtract", "multiply"):
                    raise NotModeled(f"change_local_variable's {c.key}")
                self.locals[name] = _VALUE_OPS[c.key](self.locals[name], self.operand(c, stack))
        elif k == "remove_local_variable":
            self.locals.pop(n.value, None)
        elif k in ("save_temporary_scope_as", "save_scope_as"):
            self.saved[n.value] = cur
        elif k == "clear_saved_scope":
            self.saved.pop(n.value, None)
        elif k == "change_pop_culture":
            self.change_pop_culture(n, stack)
        elif k in ("debug_log", "debug_log_scopes") and n.children is None:
            pass
        elif k in ("set_global_variable", "change_global_variable", "remove_global_variable"):
            pass
        elif k == "switch":
            case = self.switch_case(n, stack)
            if case is not None:
                self.run(case, stack)
        elif k == "hidden_effect":
            self.run(n.children, stack)
        elif _ITERATOR.match(k):
            self.iterate_effect(n, stack)
        elif k.startswith(("te_hc_", "te_hcg_")):
            self.call_effect(k, n, stack)
        elif n.children is not None and is_scope_path(k):
            self.run(n.children, stack + [self.resolve(k, stack, reading=True)])
        else:
            raise NotModeled(f"the effect {n!r}")

    def change_pop_culture(self, n, stack):
        cur = stack[-1]
        if self.ent(cur).kind != "pop":
            raise ScriptBug(f"change_pop_culture in {self.ent(cur).kind} scope")
        target, value = n.child("target"), n.child("value")
        if (n.children is None or len(n.children) != 2 or target is None or value is None
                or target.children is not None or value.children is not None or not target.value.startswith("scope:")):
            raise NotModeled(f"change_pop_culture in a form other than {{ target = scope:X value = <value name> }}: {n!r}")
        self.conversions.append((cur, target.value, self.saved.get(target.value[len("scope:"):]), value.value))

    def call_args(self, name, n, kind):
        if n.children is None:
            if kind == "effect" and n.value != "yes":
                raise ScriptBug(f"{name} = {n.value}: an effect is called with yes or an argument block")
            if kind == "trigger" and n.value not in ("yes", "no"):
                raise ScriptBug(f"{name} = {n.value}: a trigger is called with yes, no or an argument block")
            return {}
        args = {}
        for c in n.children:
            if c.op != "=" or c.children is not None or c.value is None:
                raise ScriptBug(f"{name}: each argument is a single token, not {c!r}")
            args[c.key] = c.value
        return args

    def call_effect(self, name, n, stack):
        args = self.call_args(name, n, "effect")
        self.calls.append((name, stack[-1]))
        if SELF_CHECK.match(name):
            return
        if name in self.stand_in_effects:
            self.stand_in_effects[name](self, stack, args)
            return
        body = self.script.body("effect", name, args)
        self.callstack.append(name)
        try:
            self.run(body, stack)
        finally:
            self.callstack.pop()
        if name in self.after:
            self.after[name](self, stack)

    def iterate_effect(self, n, stack):
        kind, what = _ITERATOR.match(n.key).groups()
        if kind == "any":
            raise ScriptBug(f"{n.key} used as an effect")
        if kind == "ordered":
            raise NotModeled(f"{n.key} (ordered iterators)")
        if n.children is None:
            raise ScriptBug(f"{n.key} = {n.value}")
        for c in n.children:
            if c.key in ("order_by", "max", "min", "weight", "position", "check_range_bounds", "percent"):
                raise NotModeled(f"{n.key}'s {c.key}")
        items = self.world.items(stack[-1], what)
        self.walks.append((n.key, stack[-1], tuple(self.callstack), tuple(stack)))
        limit = n.child("limit")
        body = [c for c in n.children if c.key != "limit"]
        for item in items:
            inner = stack + [item]
            if limit is None or self.holds(limit.children, inner):
                self.run(body, inner)
                if kind == "random":
                    break

    # -- triggers --

    def holds(self, nodes, stack):
        chain, taken = False, False
        for n in nodes:
            k = n.key
            if k in ("trigger_if", "trigger_else_if"):
                if k == "trigger_if":
                    chain, taken = True, False
                elif not chain:
                    raise ScriptBug("a trigger_else_if with no trigger_if before it")
                if not taken:
                    limit = n.child("limit")
                    if limit is None:
                        raise NotModeled(f"a {k} with no limit")
                    if self.holds(limit.children, stack):
                        taken = True
                        if not self.holds([c for c in n.children if c.key != "limit"], stack):
                            return False
                continue
            if k == "trigger_else":
                if not chain:
                    raise ScriptBug("a trigger_else with no trigger_if before it")
                if not taken and not self.holds(n.children, stack):
                    return False
                chain = False
                continue
            chain = False
            if not self.holds_one(n, stack):
                return False
        return True

    def holds_one(self, n, stack):
        k = n.key
        if k is None or n.op is None:
            raise NotModeled(f"the bare {n!r} in a trigger")
        if k == "limit":
            raise ScriptBug("a limit inside a trigger (an any_ iterator takes its triggers directly)")
        if k in ("AND", "OR", "NOT", "NOR", "NAND"):
            if n.children is None:
                raise ScriptBug(f"{k} = {n.value}")
            if k == "AND":
                return self.holds(n.children, stack)
            if k == "NAND":
                return not self.holds(n.children, stack)
            if k == "NOT":
                return not self.holds(n.children, stack)
            anyone = any(self.holds([c], stack) for c in n.children)
            return anyone if k == "OR" else not anyone
        if k == "always":
            return n.value == "yes"
        if k == "exists":
            return self.exists(n.value, stack)
        if k == "has_local_variable":
            return n.value in self.locals
        if k == "has_global_variable":
            return True
        if k == "switch":
            case = self.switch_case(n, stack)
            return True if case is None else self.holds(case, stack)
        if k in ("save_temporary_scope_as", "save_scope_as"):
            # Inside a trigger the engine saves the current scope as it evaluates, for the triggers after it in the
            # block to read (vanilla's guarantee_independence `possible`), and the statement holds.
            if n.children is not None or not n.value:
                raise NotModeled(f"{n!r}")
            self.saved[n.value] = stack[-1]
            return True
        if k in ("culture_percent_state", "culture_percent_country"):
            return self.culture_percent(n, stack)
        if n.children is None and self.is_value_read(k):
            return self.compare(n, stack)
        if k.startswith(("te_hc_", "te_hcg_")):
            return self.call_trigger(k, n, stack)
        m = _ITERATOR.match(k)
        if m:
            return self.iterate_trigger(n, m, stack)
        if k in _TRIGGERS:
            return _TRIGGERS[k](self, n, stack)
        if n.children is not None and is_scope_path(k):
            return self.holds(n.children, stack + [self.resolve(k, stack, reading=True)])
        if n.children is None and is_scope_path(k) and is_scope_path(n.value):
            if n.op not in ("=", "?=", "!="):
                raise NotModeled(f"{n!r}")
            try:
                left, right = self.resolve(k, stack), self.resolve(n.value, stack)
            except Missing:
                if n.op == "?=":
                    return False
                raise ScriptBug(f"{n!r} reads a scope never saved")
            return (left == right) != (n.op == "!=")
        raise NotModeled(f"the trigger {n!r}")

    def culture_percent(self, n, stack):
        """Only `culture_percent_state = { target = PREV value > 0 }` in state scope, or `culture_percent_country = {
        target = PREV value > 0 }` in country scope, entered from a culture: that culture has people in this state, or
        in a state this country holds. Any other use is not modeled."""
        kind = {"culture_percent_state": "state", "culture_percent_country": "country"}[n.key]
        target, value = n.child("target"), n.child("value")
        if (n.children is None or len(n.children) != 2 or target is None or value is None
                or target.op != "=" or target.value not in ("PREV", "prev") or value.op != ">" or value.value != "0"):
            raise NotModeled(f"{n.key} in a form other than {{ target = PREV value > 0 }}: {n!r}")
        where = self.ent(stack[-1])
        if where.kind != kind:
            raise ScriptBug(f"{n.key} in {where.kind} scope")
        culture = self.ent(self.resolve("prev", stack, reading=True))
        if culture.kind != "culture":
            raise ScriptBug(f"{n.key}'s PREV is a {culture.kind}, not a culture")
        pops = where.pops if kind == "state" else self.world.items(where.id, "scope_pop")
        return any(self.ent(pid).culture == culture.id for pid in pops)

    def switch_case(self, n, stack):
        """The body of the first case of a switch whose `trigger = case` holds, else its fallback, else None."""
        trigger = n.child("trigger")
        if n.children is None or trigger is None or trigger.value is None:
            raise NotModeled(f"a switch with no trigger: {n!r}")
        for case in n.children:
            if case.key in ("trigger", "fallback"):
                continue
            if case.children is None:
                raise NotModeled(f"a switch case that is not a block: {case!r}")
            if self.holds_one(Node(trigger.value, "=", case.key), stack):
                return case.children
        fallback = n.child("fallback")
        return fallback.children if fallback is not None else None

    def call_trigger(self, name, n, stack):
        args = self.call_args(name, n, "trigger")
        want = n.children is not None or n.value == "yes"
        if name in self.stand_in_triggers:
            got = bool(self.stand_in_triggers[name](self, stack, args))
        else:
            got = self.holds(self.script.body("trigger", name, args), stack)
        return got == want

    def iterate_trigger(self, n, m, stack):
        kind, what = m.groups()
        if kind != "any":
            raise ScriptBug(f"{n.key} used as a trigger")
        if n.children is None:
            raise ScriptBug(f"{n.key} = {n.value}")
        if n.child("percent") is not None:
            raise NotModeled(f"{n.key}'s percent")
        items = self.world.items(stack[-1], what)
        self.walks.append((n.key, stack[-1], tuple(self.callstack), tuple(stack)))
        count = n.child("count")
        conditions = [c for c in n.children if c.key != "count"]
        matched = 0
        for item in items:
            if self.holds(conditions, stack + [item]):
                matched += 1
                if count is None:
                    return True
        if count is None:
            return False
        if count.value == "all":
            return matched == len(items)
        return _COMPARE[count.op](matched, float(count.value))

    def exists(self, token, stack):
        if token.startswith("cu:"):
            raise NotModeled(f"exists = {token} (the pass names no culture)")
        if token.startswith("local_var:"):
            return token[len("local_var:"):] in self.locals
        try:
            return self.resolve(token, stack) is not None
        except Missing:
            return False

    def compare(self, n, stack):
        if n.op == "?=" and n.key.startswith("local_var:") and n.key[len("local_var:"):] not in self.locals:
            return False
        if n.op not in _COMPARE:
            raise NotModeled(f"the comparison {n!r}")
        return _COMPARE[n.op](self.read_value(n.key, stack), self.read_value(n.value, stack))

    # -- scopes and values --

    def resolve(self, path, stack, reading=False):
        idx = len(stack) - 1
        cur = stack[idx]
        linked = False
        for seg in path.split("."):
            if seg == "this":
                pass
            elif seg == "prev":
                if linked:
                    raise NotModeled(f"prev after a link in {path}")
                idx -= 1
                if idx < 0:
                    raise ScriptBug(f"{path}: no previous scope")
                cur = stack[idx]
            elif seg == "root":
                cur = stack[0]
            elif seg.startswith("scope:"):
                name = seg[len("scope:"):]
                if name not in self.saved:
                    if reading:
                        raise ScriptBug(f"{path} reads the scope {name}, never saved")
                    raise Missing(name)
                cur = self.saved[name]
            elif seg in LINKS:
                cur = self.world.link(cur, seg)
                if cur is None:
                    if reading:
                        raise ScriptBug(f"{path}: no {seg}")
                    raise Missing(seg)
            else:
                raise NotModeled(f"the scope link {seg} in {path}")
            linked = linked or seg != "prev"
        return cur

    def is_value_name(self, name):
        return name in self.value_overrides or name in self.script.values or name in vanilla_values()

    def is_value_read(self, token):
        if token.startswith("local_var:"):
            return True
        *path, last = token.split(".")
        if path and not is_scope_path(".".join(path)):
            return False
        return last.startswith("modifier:") or last in VALUE_READS or self.is_value_name(last)

    def read_value(self, token, stack):
        if token is None:
            raise NotModeled("a value with no operand")
        try:
            return float(token)
        except ValueError:
            pass
        if token in ("yes", "no"):
            return 1.0 if token == "yes" else 0.0
        if token.startswith("local_var:"):
            name = token[len("local_var:"):]
            if name not in self.locals:
                raise ScriptBug(f"a read of the unset local {name}")
            return float(self.locals[name])
        *path, last = token.split(".")
        if path:
            scope = self.resolve(".".join(path), stack, reading=True)
            stack = stack + [scope]
        return self.read_last(last, stack)

    def read_last(self, name, stack):
        e = self.ent(stack[-1])
        if name in self.value_overrides:
            value = self.value_overrides[name]
            return float(value(self, stack) if callable(value) else value)
        if name in self.script.values:
            form, text = self.script.values[name]
            if form == "scalar":
                return self.read_value(text, stack)
            return self.eval_value(self.script.body("value", name), stack)
        if name in vanilla_values():
            return vanilla_values()[name]
        if name.startswith("modifier:"):
            return self.world.modifier(e.id, name[len("modifier:"):])
        if name in VALUE_READS:
            if e.kind != VALUE_READS[name]:
                raise ScriptBug(f"{name} read on a {e.kind}")
            return float({"pop_radical_fraction": lambda: e.radicals, "total_size": lambda: e.size,
                          "pop_acceptance": lambda: e.acceptance, "culture_current_fervor": lambda: e.fervor}[name]())
        raise NotModeled(f"the value {name} read on a {e.kind}")

    def operand(self, n, stack):
        if n.children is not None:
            return self.eval_value(n.children, stack)
        return self.read_value(n.value, stack)

    def eval_value(self, nodes, stack, total=0.0):
        chain, taken = False, False
        for n in nodes:
            k = n.key
            if k in ("if", "else_if"):
                if k == "if":
                    chain, taken = True, False
                elif not chain:
                    raise ScriptBug("an else_if with no if before it")
                if not taken:
                    limit = n.child("limit")
                    if limit is None:
                        raise NotModeled(f"an {k} with no limit in a value")
                    if self.holds(limit.children, stack):
                        taken = True
                        total = self.eval_value([c for c in n.children if c.key != "limit"], stack, total)
                continue
            if k == "else":
                if not chain:
                    raise ScriptBug("an else with no if before it")
                if not taken:
                    total = self.eval_value(n.children, stack, total)
                chain = False
                continue
            chain = False
            if k == "desc":
                continue
            if k == "divide":
                divisor = self.operand(n, stack)
                if divisor == 0:
                    raise ScriptBug("a division by zero in a value")
                total /= divisor
                continue
            if k not in _VALUE_OPS:
                raise NotModeled(f"the value operation {n!r}")
            total = _VALUE_OPS[k](total, self.operand(n, stack))
        return total


def _culture_scope(interp, stack, what):
    e = interp.ent(stack[-1])
    if e.kind != "culture":
        raise ScriptBug(f"{what} in {e.kind} scope")
    return e


def _target(interp, n, stack, kind):
    if n.children is not None:
        raise NotModeled(f"{n.key} with a block")
    e = interp.ent(interp.resolve(n.value, stack, reading=True))
    if e.kind != kind:
        raise ScriptBug(f"{n!r}: the target is a {e.kind}, not a {kind}")
    return e


def _heritage_group(interp, n, stack):
    culture = _culture_scope(interp, stack, n.key)
    if not n.value.startswith("heritage_group_"):
        raise NotModeled(f"{n!r} (only heritage groups are modeled)")
    return culture.group == n.value[len("heritage_group_"):]


def _trait(interp, n, stack):
    culture = _culture_scope(interp, stack, n.key)
    return n.value in (culture.heritage, f"language_{culture.language}")


def _primaries(interp, n, stack):
    return [interp.ent(c) for c in _target(interp, n, stack, "country").primaries]


def _homeland(interp, n, stack):
    culture = _culture_scope(interp, stack, n.key)
    target = interp.ent(interp.resolve(n.value, stack, reading=True))
    region = target.region if target.kind == "state" else target.id if target.kind == "region" else None
    if region is None:
        raise ScriptBug(f"{n!r}: the target is a {target.kind}")
    return region in culture.homelands


def _is_homeland(interp, n, stack):
    region = interp.ent(stack[-1])
    if region.kind != "region":
        raise ScriptBug(f"is_homeland in {region.kind} scope")
    return region.id in _target(interp, n, stack, "culture").homelands


def _homeland_of_country_cultures(interp, n, stack):
    state = interp.ent(stack[-1])
    if state.kind != "state":
        raise ScriptBug(f"is_homeland_of_country_cultures in {state.kind} scope")
    return state.region in interp.world.primary_homelands(_target(interp, n, stack, "country").id)


def _community_in(interp, n, stack):
    culture = _culture_scope(interp, stack, n.key)
    state = _target(interp, n, stack, "state")
    return any(interp.ent(pid).culture == culture.id for pid in state.pops)


def _incorporated(interp, n, stack):
    state = interp.ent(stack[-1])
    if state.kind != "state" or n.value not in ("yes", "no"):
        raise ScriptBug(f"{n!r} in {state.kind} scope")
    return state.incorporated == (n.value == "yes")


def _pop_type(interp, n, stack):
    pop = interp.ent(stack[-1])
    if pop.kind != "pop":
        raise ScriptBug(f"is_pop_type in {pop.kind} scope")
    if n.value != "slaves":
        raise NotModeled(f"{n!r} (only slaves is modeled)")
    return pop.slave


_TRIGGERS = {
    "has_discrimination_trait_group": _heritage_group,
    "has_discrimination_trait": _trait,
    "shares_heritage_trait_group_with_any_primary_culture":
        lambda i, n, s: any(p.group == _culture_scope(i, s, n.key).group for p in _primaries(i, n, s)),
    "shares_heritage_trait_with_any_primary_culture":
        lambda i, n, s: any(p.heritage == _culture_scope(i, s, n.key).heritage for p in _primaries(i, n, s)),
    "shares_heritage_trait_group_with_culture":
        lambda i, n, s: _target(i, n, s, "culture").group == _culture_scope(i, s, n.key).group,
    "shares_heritage_trait_with_culture":
        lambda i, n, s: _target(i, n, s, "culture").heritage == _culture_scope(i, s, n.key).heritage,
    "shares_language_trait_with_culture":
        lambda i, n, s: _target(i, n, s, "culture").language == _culture_scope(i, s, n.key).language,
    "is_primary_culture_of":
        lambda i, n, s: _culture_scope(i, s, n.key).id in _target(i, n, s, "country").primaries,
    "has_homeland": _homeland,
    "is_homeland": _is_homeland,
    "is_homeland_of_country_cultures": _homeland_of_country_cultures,
    "is_incorporated": _incorporated,
    "culture_has_community_in_state": _community_in,
    "is_pop_type": _pop_type,
}


# ---------------------------------------------------------------------------------------------------------------
# Worlds
# ---------------------------------------------------------------------------------------------------------------

_SCRIPT = None


def script():
    global _SCRIPT
    if _SCRIPT is None:
        _SCRIPT = Script()
    return _SCRIPT


def country_modifiers(blocked=0, cross=0.0, allowed=STATUSES, mults=None):
    mods = {BLOCKED: float(blocked), SHARE: float(cross)}
    for status in STATUSES:
        mods[f"country_allow_assimilation_{status}_bool"] = 1.0 if status in allowed else 0.0
        mods[f"country_assimilation_{status}_mult"] = (mults or {}).get(status, 0.0)
    return mods


def pass_locals(mode=1, blocked=0, cross=0.0):
    """The country locals the brief has te_hc_yearly_country set, for a helper run on its own."""
    can = 0 if (blocked and mode in (2, 3)) or (mode == 3 and cross == 0) else 1
    return {"te_hc_mode": mode, "te_hc_cross": cross, "te_hc_blocked": blocked, "te_hc_can": can}


def expected(mode, speaks, targets, local, blocked, slave, cross, group, host=True):
    """The outcome table: (target token, value name), or None where nothing converts."""
    if not host:
        return None
    if mode == 1 and not speaks and local > 0:
        return f"scope:te_hc_l_{group}", STEP
    if mode == 1 and not speaks and targets:
        return f"scope:te_hc_t_{group}", STEP
    if mode == 2:
        return None if blocked or slave else ("scope:te_hc_host", STEP)
    return None if blocked or slave or cross == 0 else ("scope:te_hc_host", CROSS_STEP)


def other_group(group):
    return GROUPS[(GROUPS.index(group) + 1) % len(GROUPS)]


def _pick_host_stand_in(interp, stack, args):
    state = interp.ent(stack[-1])
    if state.facts["host"]:
        interp.saved["te_hc_host"] = state.facts["host_culture"]
        interp.locals["te_hc_has_host"] = 1


def _save_targets_stand_in(interp, stack, args):
    # As the generated ladder: every hybrid of the host's language, none for the language's own heritage group.
    state = interp.ent(stack[-1])
    if state.facts["targets"]:
        for group in GROUPS:
            if group != state.facts.get("no_hybrid"):
                interp.saved[f"te_hc_t_{group}"] = f"HYB_{group}_{state.id}"
        interp.locals["te_hc_has_targets"] = 1


def _find_locals_stand_in(interp, stack, args):
    state = interp.ent(stack[-1])
    for group in GROUPS:
        interp.locals[f"te_hc_has_local_{group}"] = 0
    for group, level in state.facts["locals"].items():
        if level:
            interp.locals[f"te_hc_has_local_{group}"] = level
            interp.saved[f"te_hc_l_{group}"] = f"LOC_{group}_{state.id}"


def table_world(row, host=True, stale=True, no_hybrid=None, state_mult=0.0):
    """One country whose pass reaches state S1 with the row's facts. S1 holds P1 first, of the next heritage group,
    which takes the language step under Hybrid Cultures (so a per-pop flag left at 1 shows), then P, the row's pop.
    With `stale`, S0 is walked first with a host of another language, its hybrids, and every group's local culture,
    and no pops: the scopes it saved are still there when S1 is passed. SC is the capital, with no culture of another
    group. `no_hybrid` is a group S1's host language has no hybrid for (the language's own group); `state_mult` is
    S1's assimilation sum."""
    group, y = row["group"], other_group(row["group"])
    w = World(mode=row["mode"])
    w.culture("C_HOST", "european", "l_host")
    w.culture("C_HOST0", "european", "l_stale")
    w.culture("C_P", group, "l_host" if row["speaks"] else "l_pop")
    w.culture("C_P1", y, "l_pop1")
    w.country("OWNER", ["C_HOST"], capital="SC", modifiers=country_modifiers(row["blocked"], row["cross"]))
    states = []
    if stale:
        states.append(w.state("S0", "OWNER", other=True, host=True, host_culture="C_HOST0", targets=True,
                              locals={g: 2 for g in GROUPS}))
    states.append(w.state("S1", "OWNER", other=True, host=host, host_culture="C_HOST", targets=row["targets"],
                          locals={group: row["local"], y: 1}, no_hybrid=no_hybrid,
                          modifiers={STATE_MULT: state_mult}))
    w.state("SC", "OWNER", other=False, host=True, host_culture="C_HOST", targets=False, locals={})
    for sid in states:
        language = w.ents[w.ents[sid].facts["host_culture"]].language
        for g in GROUPS:
            w.culture(f"HYB_{g}_{sid}", g, language)
            w.culture(f"LOC_{g}_{sid}", g, language)
    w.pop("P1", "S1", "C_P1")
    w.pop("P", "S1", "C_P", slave=row["slave"])
    w.pop("P_CAP", "SC", "C_HOST")
    return w


def _in_scope(interp, stack, kind, what):
    e = interp.ent(stack[-1])
    if e.kind != kind:
        raise ScriptBug(f"{what} in {e.kind} scope")
    return e


def run_table_world(world, cross, real_values=False):
    """The pass over a table world. The fractions are stood in for (rate 0.024) unless `real_values`, when the
    values file is read as written."""
    interp = Interp(
        script(), world,
        effects={"te_hc_pick_host": _pick_host_stand_in, "te_hcg_save_targets": _save_targets_stand_in,
                 "te_hc_find_locals": _find_locals_stand_in},
        triggers={"te_hc_state_has_other_group":
                  lambda i, s, a: _in_scope(i, s, "state", "te_hc_state_has_other_group").facts["other"],
                  "te_hc_pop_taken": lambda i, s, a: bool(_in_scope(i, s, "pop", "te_hc_pop_taken")),
                  "te_hc_speaks_host":
                  lambda i, s, a: i.ent(_in_scope(i, s, "pop", "te_hc_speaks_host").culture).language == "l_host"},
        values=None if real_values else {"te_hc_pop_rate": 0.024, STEP: 0.024, CROSS_STEP: 0.024 * cross},
    )
    interp.run_effect("te_hc_yearly_country", ["OWNER"])
    return interp


def conversions_of(interp, pop):
    return [(target, value) for who, target, _, value in interp.conversions if who == pop]


def wrong_scopes(interp):
    """Conversions into a scope saved for another state than S1: a stale host, hybrid or local culture."""
    out = []
    for pop, target, saved, value in interp.conversions:
        name = target[len("scope:"):]
        want = {"te_hc_host": "C_HOST"}.get(name)
        if name.startswith("te_hc_t_"):
            want = f"HYB_{name[len('te_hc_t_'):]}_S1"
        elif name.startswith("te_hc_l_"):
            want = f"LOC_{name[len('te_hc_l_'):]}_S1"
        if saved != want:
            out.append(f"{pop} into {target}, which holds {saved}, not {want}")
    return out


def table_rows(mode):
    for speaks in (False, True):
        for targets in (0, 1):
            for local in (0, 1, 2):
                for blocked in (0, 1):
                    for slave in (False, True):
                        for cross in (0.0, 0.5, 1.0):
                            groups = GROUPS if mode == 1 and not speaks else GROUPS[::3]
                            for group in groups:
                                yield dict(mode=mode, speaks=speaks, targets=targets, local=local, blocked=blocked,
                                           slave=slave, cross=cross, group=group)


def check_rows(rows, host=True):
    """Every row through the pass, with and without a stale state before it: mismatch lines, or []."""
    bad = []
    for row in rows:
        for stale in (True, False):
            interp = run_table_world(table_world(row, host=host, stale=stale), row["cross"])
            pop1 = dict(row, speaks=False, slave=False, local=1, group=other_group(row["group"]))
            for pop, facts in (("P", row), ("P1", pop1)):
                want = expected(**facts, host=host)
                got = conversions_of(interp, pop)
                if got != ([want] if want else []):
                    bad.append(f"{pop} {facts} stale={stale}: expected {want}, got {got}")
            bad += [f"{row} stale={stale}: {line}" for line in wrong_scopes(interp)]
    return bad


def report(bad, limit=25):
    lines = bad[:limit] + ([f"... and {len(bad) - limit} more"] if len(bad) > limit else [])
    return f"{len(bad)} mismatches:\n" + "\n".join(lines)


def pop_world(acceptance=90.0, homeland=False, allowed=STATUSES, state_bool=0, group="african", trait=None,
              primaries=(("C_HOST", "european", "heritage_host"),)):
    """One pop P of culture C_P in S1, for the pop triggers; the owner's primary cultures as given."""
    w = World(mode=1)
    for cid, g, heritage in primaries:
        w.culture(cid, g, "l_host", heritage=heritage)
    w.culture("C_P", group, "l_pop", heritage=trait, homelands={"R_S1"} if homeland else {"R_ELSEWHERE"})
    w.country("OWNER", [p[0] for p in primaries], capital="S1", modifiers=country_modifiers(allowed=allowed))
    w.state("S1", "OWNER", modifiers={HOMELAND_BOOL: float(state_bool)})
    w.pop("P_HOST", "S1", primaries[0][0])
    w.pop("P", "S1", "C_P", acceptance=acceptance)
    return w


def pop_interp(world, **kwargs):
    host = world.ents["OWNER"].primaries[0]
    return Interp(script(), world, locals_=pass_locals(), saved={"te_hc_owner": "OWNER", "te_hc_state": "S1",
                                                                  "te_hc_host": host}, **kwargs)


POP_STACK = ["OWNER", "S1", "P"]


def rate_world(state_mult=0.0, status="full_acceptance", status_mult=0.0, other_mult=7.0, radicals=0.0, fervor=0.0,
               homeland=False, size=1000, cross=1.0):
    """One pop for the script values. The other statuses' multipliers are set wide of the pop's, so a read of the
    wrong one shows."""
    w = World(mode=1)
    w.culture("C_HOST", "european", "l_host")
    w.culture("C_P", "african", "l_pop", homelands={"R_S1"} if homeland else {"R_ELSEWHERE"}, fervor=fervor)
    mults = {s: (status_mult if s == status else other_mult) for s in STATUSES}
    w.country("OWNER", ["C_HOST"], capital="S1", modifiers=country_modifiers(cross=cross, mults=mults))
    w.state("S1", "OWNER", modifiers={STATE_MULT: state_mult})
    w.pop("P", "S1", "C_P", size=size, acceptance=ACCEPTANCE_IN[status], radicals=radicals)
    return w


def value_in(world, name, stack=POP_STACK, values=None):
    cross = world.ents["OWNER"].modifiers[SHARE]
    interp = Interp(script(), world, values=values, locals_=pass_locals(cross=cross),
                    saved={"te_hc_owner": "OWNER", "te_hc_state": "S1", "te_hc_host": "C_HOST"})
    return interp.value(name, stack)


def callees(text, table):
    """Every scripted name in `table` that `text` calls, transitively, `text`'s own included."""
    seen, todo = [], [text]
    while todo:
        for name in re.findall(r"\b(te_hc\w*)\s*=", todo.pop()):
            if name in table and name not in seen:
                seen.append(name)
                todo.append(table[name][1])
    return seen


def yearly_walk(world, **stand_ins):
    """te_hc_yearly_country with te_hc_state_pass stood in for: the states it passes, in order."""
    walked = []
    effects = {"te_hc_state_pass": lambda i, stack, args: walked.append(stack[-1])}
    interp = Interp(script(), world, effects=effects, **stand_ins)
    interp.run_effect("te_hc_yearly_country", ["OWNER"])
    return walked, interp


def mode_world(mode, blocked=0, cross=1.0):
    w = World(mode=mode)
    w.culture("C_HOST", "european", "l_host")
    w.culture("C_X", "african", "l_x")
    w.country("OWNER", ["C_HOST"], capital="S1", modifiers=country_modifiers(blocked, cross))
    w.state("S1", "OWNER")
    w.pop("P_HOST", "S1", "C_HOST")
    w.pop("P_X", "S1", "C_X")
    return w


# ---------------------------------------------------------------------------------------------------------------
# The outcome table
# ---------------------------------------------------------------------------------------------------------------

class OutcomeTableTest(unittest.TestCase):
    """Each row of the outcome table, crossed with blocked, slave and the crossing share, and with every heritage
    group for the rows that name one: the pass from te_hc_yearly_country down, te_hc_pick_host, te_hc_find_locals
    and te_hcg_save_targets stood in for with the row's host, local culture and targets. Each asserts the scope the
    pop converts into, saved in this state, and which fraction it is given, or that it does not convert."""

    def test_hybrid_cultures_rows(self):
        bad = check_rows(table_rows(1))
        self.assertFalse(bad, report(bad))

    def test_unrestricted_rows(self):
        bad = check_rows(table_rows(2))
        self.assertFalse(bad, report(bad))

    def test_none_rows(self):
        bad = check_rows(table_rows(3))
        self.assertFalse(bad, report(bad))

    def test_a_zero_rate_calls_nothing(self):
        # Changes note 2: a taken pop whose rate is 0 gets no change_pop_culture at all, under every setting. The rate
        # is 0 through the state's sum (-100%) or the status's (-100%), the values file read as written.
        bad, converted = [], []
        for mode in (1, 2, 3):
            for row in table_rows(mode):
                if row["group"] != "african":
                    continue
                for zero in ("state", "status"):
                    world = table_world(row, state_mult=-1.0 if zero == "state" else 0.0)
                    if zero == "status":
                        world.ents["OWNER"].modifiers["country_assimilation_full_acceptance_mult"] = -1.0
                    interp = run_table_world(world, row["cross"], real_values=True)
                    if interp.conversions:
                        bad.append(f"{row} rate 0 by the {zero} sum: {interp.conversions}")
            # The same worlds at the base rate do convert, so the check above is not vacuous.
            row = dict(mode=mode, speaks=True, targets=0, local=0, blocked=0, slave=False, cross=1.0, group="african")
            converted.append(bool(run_table_world(table_world(row), 1.0, real_values=True).conversions))
        self.assertFalse(bad, report(bad))
        self.assertEqual(converted, [True, True, True])

    def test_a_hybrid_of_another_language_is_not_a_target(self):
        # Changes note 3: the ladder saves no hybrid for the host language's own heritage group, so te_hc_t_<group>
        # can still hold an earlier state's hybrid of another language. With te_hc_has_targets = 1, a pop of that
        # group takes no language step there and is handled by the joining branch, as if there were no targets.
        bad = []
        for group in GROUPS:
            for blocked in (0, 1):
                for slave in (False, True):
                    for cross in (0.0, 0.5, 1.0):
                        row = dict(mode=1, speaks=False, targets=1, local=0, blocked=blocked, slave=slave,
                                   cross=cross, group=group)
                        for stale in (True, False):
                            interp = run_table_world(table_world(row, stale=stale, no_hybrid=group), cross)
                            want = expected(**dict(row, targets=0))
                            got = conversions_of(interp, "P")
                            if got != ([want] if want else []):
                                bad.append(f"{row} stale={stale}: expected {want}, got {got}")
                            bad += [f"{row} stale={stale}: {line}" for line in wrong_scopes(interp)]
        self.assertFalse(bad, report(bad))

    def test_speaking_the_hosts_language_is_a_shared_language_trait(self):
        # te_hc_speaks_host, stood in for above: shares_language_trait_with_culture = scope:te_hc_host.
        for language, speaks in (("l_host", True), ("l_pop", False)):
            world = pop_world()
            world.ents["C_P"].language = language
            self.assertEqual(pop_interp(world).trigger("te_hc_speaks_host", POP_STACK), speaks, language)


# ---------------------------------------------------------------------------------------------------------------
# The shape of the pass
# ---------------------------------------------------------------------------------------------------------------

class PulseTest(unittest.TestCase):
    def test_the_pulse_is_the_yearly_country_one(self):
        nodes = parse(code(ON_ACTIONS))
        hooks = [n for n in nodes if n.key == "on_yearly_pulse_country"]
        listed = [c.key for n in hooks for lst in n.children if lst.key == "on_actions" for c in lst.children]
        self.assertIn("te_hc_yearly_on_action", listed)
        action = [n for n in nodes if n.key == "te_hc_yearly_on_action"]
        self.assertEqual(len(action), 1)
        effect = action[0].child("effect")
        self.assertIsNotNone(effect, "te_hc_yearly_on_action has no effect")
        self.assertIn("te_hc_yearly_country = yes", [repr(n) for n in effect.children],
                      "the on_action's effect does not run te_hc_yearly_country = yes unconditionally")
        # Once a year: the on_action hangs off no other pulse, and nothing else runs the pass.
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").rglob("*.txt")):
            text = strip_comments(read(path))
            if path != ON_ACTIONS:
                self.assertNotIn("te_hc_yearly_on_action", text, path.name)
                self.assertNotRegex(text, r"\bte_hc_yearly_country\s*=\s*yes\b", path.name)
        for hook in (n for n in nodes if n.key != "on_yearly_pulse_country" and n.children):
            lists = [c.key for lst in hook.children if lst.key == "on_actions" for c in lst.children or ()]
            self.assertNotIn("te_hc_yearly_on_action", lists, hook.key)
        self.assertEqual(len(re.findall(r"\bte_hc_yearly_country\s*=\s*yes\b", code(ON_ACTIONS))), 1)

    def test_the_pass_runs_under_every_setting(self):
        # Every setting walks the states; only te_hc_can (nothing can convert this year) may stop it.
        for mode in (1, 2, 3):
            with self.subTest(mode=mode):
                walked, _ = yearly_walk(mode_world(mode))
                self.assertEqual(walked, ["S1"])
        # No rule test around the walk: not in the on_action, not in the limits that lead to it.
        action = next(n for n in parse(code(ON_ACTIONS)) if n.key == "te_hc_yearly_on_action")
        for word in RULE_WORDS:
            self.assertNotIn(word, words(" ".join(map(repr, action.children))))
        yearly = script().body("effect", "te_hc_yearly_country")
        guards = guards_of(yearly, lambda n: re.match(r"(every|random|ordered)_scope_state$", n.key or ""))
        self.assertTrue(guards, "te_hc_yearly_country walks no states")
        triggers = script().triggers
        for limits in guards:
            text = " ".join(repr(n) for n in limits)
            text += " " + " ".join(triggers[name][1] for name in callees(text, triggers))
            for word in RULE_WORDS:
                self.assertNotIn(word, text)

    def test_only_incorporated_states_are_walked(self):
        # Review Focus 5. SA is incorporated with a culture of another group; SB the same but unincorporated; SC
        # incorporated with only the owner's group. Only SA is passed, and only te_hc_yearly_country passes a state.
        w = World(mode=2)
        w.culture("C_HOST", "european", "l_host")
        w.culture("C_X", "african", "l_x")
        w.country("OWNER", ["C_HOST"], capital="SC", modifiers=country_modifiers(cross=1.0))
        w.state("SA", "OWNER")
        w.state("SB", "OWNER", incorporated=False)
        w.state("SC", "OWNER")
        for sid in ("SA", "SB"):
            w.pop(f"P_X_{sid}", sid, "C_X")
        for sid in ("SA", "SB", "SC"):
            w.pop(f"P_H_{sid}", sid, "C_HOST")
        walked, _ = yearly_walk(w)
        self.assertEqual(walked, ["SA"])
        calls = [(path.name, len(re.findall(r"\bte_hc_state_pass\s*=\s*yes\b", code(path)))) for path in PASS_FILES]
        self.assertEqual([c for c in calls if c[1]], [(EFFECTS.name, 1)])
        self.assertTrue(re.search(r"\bte_hc_state_pass\s*=\s*yes\b", body_text(EFFECTS, "te_hc_yearly_country")))

    def test_no_world_iterator(self):
        # Within the pass; a once-a-game self-check (te_hc_chk_*) may look wider.
        world = re.compile(r"\b(every|any|random|ordered)_(state|country|pop|culture|state_region|province)\b")
        for path in PASS_FILES:
            for name, (form, text) in top_level(path).items():
                if not SELF_CHECK.match(name):
                    self.assertFalse(world.findall(text), f"{path.name}: {name}")


def is_zero(token):
    return bool(token) and re.fullmatch(r"(0+(\.0*)?|no)", token) is not None


def guards_of(nodes, target, above=()):
    """For each node `target` picks, the limits that decide whether it runs: of each if/else_if/else above it (with
    the chain's earlier branches) and its own."""
    found = []
    chain = []
    for n in nodes:
        if n.key == "if":
            chain = []
        if n.key in ("if", "else_if", "else") and n.children is not None:
            limits = [c for b in chain + [n] for c in (b.child("limit").children if b.child("limit") else [])]
            found += guards_of(n.children, target, above + tuple(limits))
            chain.append(n)
            continue
        chain = []
        if n.children is None:
            continue
        if target(n):
            own = n.child("limit")
            found.append(list(above) + (own.children if own else []))
        else:
            found += guards_of(n.children, target, above)
    return found


class HostTest(unittest.TestCase):
    def test_host_and_target_flags_are_reset_before_anything_reads_them(self):
        # Review Focus 2: a host or a set of targets saved in an earlier state is never acted on.
        state_pass = script().body("effect", "te_hc_state_pass")
        head = []
        for n in state_pass:
            if n.key not in ("set_local_variable", "save_temporary_scope_as", "save_scope_as"):
                break
            head.append(n)
        reset = {n.child("name").value: n.child("value").value for n in head if n.key == "set_local_variable"}
        self.assertTrue(is_zero(reset.get("te_hc_has_host")), "te_hc_state_pass does not open by clearing te_hc_has_host")
        self.assertTrue(is_zero(reset.get("te_hc_has_targets")), "nor te_hc_has_targets")
        # The hand-written pass only ever clears te_hc_has_targets; te_hcg_save_targets alone sets it, behind a guard.
        for path in (EFFECTS, TRIGGERS, VALUES):
            for node in walk_nodes(parse(code(path))):
                if node.key == "set_local_variable" and node.child("name") and \
                        node.child("name").value == "te_hc_has_targets":
                    self.assertTrue(is_zero(node.child("value").value), f"{path.name}: {node!r}")
        # Run: S0 leaves a host and targets saved; S1 has neither, so nothing in S1 converts into them.
        for mode in (1, 2, 3):
            row = dict(mode=mode, speaks=False, targets=0, local=0, blocked=0, slave=False, cross=1.0, group="african")
            interp = run_table_world(table_world(row, host=False, stale=True), 1.0)
            self.assertEqual(interp.conversions, [], f"mode {mode}")
        row = dict(mode=1, speaks=False, targets=0, local=0, blocked=0, slave=False, cross=1.0, group="african")
        interp = run_table_world(table_world(row, host=True, stale=True), 1.0)
        self.assertEqual(conversions_of(interp, "P"), [("scope:te_hc_host", CROSS_STEP)])
        self.assertEqual(wrong_scopes(interp), [])

    def test_nothing_converts_without_a_host(self):
        bad = []
        for mode in (1, 2, 3):
            bad += check_rows((r for r in table_rows(mode) if r["group"] == "african"), host=False)
        self.assertFalse(bad, report(bad))
        # The same world with a host does convert, so the check above is not vacuous.
        row = dict(mode=2, speaks=False, targets=0, local=0, blocked=0, slave=False, cross=1.0, group="african")
        self.assertEqual(conversions_of(run_table_world(table_world(row), 1.0), "P"), [("scope:te_hc_host", STEP)])

    def test_a_state_without_a_primary_culture_takes_the_capitals_host(self):
        # Review Focus 5. Primaries A and B; the capital SC is mostly A. S1 and S2 have no primary culture and take
        # the capital's host, worked out once; S3 has more B than A; S4 has A alone, picked with no pop walk.
        hosts, interp = self.hosts([("S1", [("C_X", 300)]), ("S2", [("C_Y", 200)]),
                                    ("S3", [("C_B", 400), ("C_A", 100), ("C_X", 50)]),
                                    ("S4", [("C_A", 50), ("C_X", 500)]),
                                    ("SC", [("C_A", 500), ("C_B", 100), ("C_X", 50)])])
        self.assertEqual(hosts, {"S1": ("C_A", 1), "S2": ("C_A", 1), "S3": ("C_B", 1), "S4": ("C_A", 1),
                                 "SC": ("C_A", 1)})
        # A count is an every_scope_pop walk (total_size into a local); an any_scope_pop test of presence is not one.
        counting = [w for w in interp.walks if w[0] == "every_scope_pop" and "te_hc_pick_host" in w[2]]
        self.assertEqual([w for w in counting if w[1] == "S4"], [], "one primary culture present: no pop walk")
        self.assertTrue([w for w in counting if w[1] == "S3"], "two primary cultures present: counted by pop walks")
        # The capital's pops are counted at most once a pass beyond SC's own state pass: once per primary culture.
        capital = [w for w in interp.walks if w[0] == "every_scope_pop" and w[1] == "SC"
                   and (len(w[3]) < 2 or w[3][1] != "SC")]
        self.assertLessEqual(len(capital), 2, capital)
        # The capital has no primary culture either: any primary culture with people in the country (changes note 4).
        # A lives only in S5; B nowhere in the country.
        hosts, _ = self.hosts([("S1", [("C_X", 300)]), ("S5", [("C_A", 80), ("C_X", 20)]), ("SC", [("C_X", 100)])])
        self.assertEqual(hosts["S1"], ("C_A", 1))
        # No primary culture has anyone in the country: no host, and nothing converts in that state.
        hosts, interp = self.hosts([("S1", [("C_X", 300)]), ("SC", [("C_X", 100)])], taken=True)
        self.assertEqual(hosts["S1"][1], 0, hosts)
        self.assertEqual([c for c in interp.conversions if c[0].startswith("P_S1_")], [])
        # The same pops with a primary culture living in the country do convert in S1, so that is not vacuous.
        hosts, interp = self.hosts([("S1", [("C_X", 300)]), ("S5", [("C_A", 80)]), ("SC", [("C_X", 100)])],
                                   taken=True)
        self.assertEqual([c[:2] for c in interp.conversions if c[0].startswith("P_S1_")],
                         [("P_S1_0", "scope:te_hc_host")])

    def hosts(self, layout, taken=False):
        """The pass under Unrestricted over the layout's states; each state's host and te_hc_has_host after its pass.
        With `taken`, every pop that is not of a primary culture is taken, so conversions show."""
        w = World(mode=2)
        w.culture("C_A", "european", "l_a")
        w.culture("C_B", "european", "l_b")
        w.culture("C_X", "african", "l_x")
        w.culture("C_Y", "south_asian", "l_y")
        w.country("OWNER", ["C_A", "C_B"], capital="SC", modifiers=country_modifiers(cross=1.0))
        for sid, pops in layout:
            w.state(sid, "OWNER")
            for n, (culture, size) in enumerate(pops):
                w.pop(f"P_{sid}_{n}", sid, culture, size=size)
        hosts = {}
        interp = Interp(script(), w,
                        effects={"te_hcg_save_targets": lambda i, s, a: None,
                                 "te_hc_find_locals": _find_locals_stand_in_empty},
                        triggers={"te_hc_pop_taken":
                                  lambda i, s, a: taken and i.ent(s[-1]).culture not in ("C_A", "C_B")})
        interp.after["te_hc_state_pass"] = lambda i, stack: hosts.__setitem__(
            stack[-1], (i.saved.get("te_hc_host"), i.locals.get("te_hc_has_host")))
        interp.run_effect("te_hc_yearly_country", ["OWNER"])
        return hosts, interp


def _find_locals_stand_in_empty(interp, stack, args):
    for group in GROUPS:
        interp.locals[f"te_hc_has_local_{group}"] = 0


class TakenTest(unittest.TestCase):
    def test_the_taken_test_is_by_heritage_group_against_every_primary_culture(self):
        # Review Focus 4, Paraguay: primary cultures of two heritage groups, the state's host the Indigenous
        # American one. A European pop shares a group with the other primary culture, not the host: not taken. A
        # culture sharing a group but not a heritage trait (a Pole in Germany) is not taken either.
        primaries = (("C_HOST", "indigenous_american", "heritage_guarani"), ("C_OTHER", "european", "heritage_latin"))
        for group, trait, taken in (("european", "heritage_italian", False), ("european", "heritage_latin", False),
                                    ("indigenous_american", "heritage_aymara", False),
                                    ("african", "heritage_yoruba", True), ("south_asian", "heritage_bengali", True)):
            with self.subTest(group=group, trait=trait):
                world = pop_world(group=group, trait=trait, primaries=primaries)
                self.assertEqual(pop_interp(world).trigger("te_hc_pop_taken", POP_STACK), taken)
        # The state test is the same, by group against every primary culture: a state of only European and
        # Indigenous American people has no culture of another group.
        for group, other in (("european", False), ("african", True)):
            with self.subTest(state_with=group):
                world = pop_world(group=group, primaries=primaries)
                self.assertEqual(pop_interp(world).trigger("te_hc_state_has_other_group", ["OWNER", "S1"]), other)
        state_test = words(body_text(TRIGGERS, "te_hc_state_has_other_group"))
        self.assertIn("any_scope_culture", state_test)
        self.assertIn("shares_heritage_trait_group_with_any_primary_culture", state_test)

    def test_a_pop_in_its_homeland_is_taken_only_with_the_state_bool(self):
        for homeland in (False, True):
            for state_bool in (0, 1):
                with self.subTest(homeland=homeland, state_bool=state_bool):
                    world = pop_world(homeland=homeland, state_bool=state_bool)
                    self.assertEqual(pop_interp(world).trigger("te_hc_pop_taken", POP_STACK),
                                     not homeland or bool(state_bool))

    def test_the_status_ladder_covers_five_statuses_at_vanillas_thresholds(self):
        for acceptance in (0, 10, 19.5, 20, 30, 39.5, 40, 50, 59.5, 60, 70, 79.5, 80, 90, 100):
            status = status_of(acceptance)
            for allowed in [(s,) for s in STATUSES] + [STATUSES, ()]:
                with self.subTest(acceptance=acceptance, allowed=allowed):
                    world = pop_world(acceptance=acceptance, allowed=allowed)
                    interp = pop_interp(world)
                    self.assertEqual(interp.trigger("te_hc_pop_status_allowed", POP_STACK), status in allowed)
                    self.assertEqual(interp.trigger("te_hc_pop_taken", POP_STACK), status in allowed)
        triggers = script().triggers
        text = " ".join(triggers[name][1] for name in callees("te_hc_pop_status_allowed =", triggers))
        for number in (2, 3, 4, 5):
            self.assertRegex(text, rf"\bacceptance_status_{number}\b")
        for status in STATUSES:
            self.assertIn(f"country_allow_assimilation_{status}_bool", text)


class OnePersonFloorTest(unittest.TestCase):
    def test_a_fraction_above_zero_converts_at_least_one_person_and_zero_converts_nobody(self):
        # Changes note 1: the small-pop rule (a pop under 50 converting whole) is gone. Where the fraction is above 0
        # at least one person converts (the engine's MIN_ASSIMILATION = 1, once a year): the fraction is floored at
        # 1 / the pop's size, never above 1. A fraction of 0 (a rate of 0, or a crossing share of 0) stays 0.
        self.assertNotRegex(code(VALUES), r"\bte_hc_small_pop\b", "te_hc_small_pop is back in the values file")
        for path in PASS_FILES:
            self.assertNotIn("te_hc_small_pop", code(path), path.name)
        cases = [
            # (size, state_mult, share, te_hc_pop_step, te_hc_pop_cross_step): the note's worked figures first.
            (1000, 0.0, 1.0, 0.024, 0.024),
            (24, 0.0, 1.0, 1 / 24, 1 / 24),          # 0.0417, not the whole pop
            (1, 0.0, 1.0, 1.0, 1.0),
            (1000, 0.0, 0.5, 0.024, 0.012),
            (24, 0.0, 0.5, 1 / 24, 1 / 24),
            (1000, 0.0, 0.0, 0.024, 0.0),            # share 0: nobody crosses, at any size
            (24, 0.0, 0.0, 1 / 24, 0.0),
            (1, 0.0, 0.0, 1.0, 0.0),
            (1000, -1.0, 1.0, 0.0, 0.0),             # rate 0: nobody, at any size
            (24, -1.0, 0.5, 0.0, 0.0),
            (1, -1.0, 1.0, 0.0, 0.0),
            (10, -3.0, 0.5, 0.0, 0.0),
            # Either side of the floor: 1/41 = 0.0244 is above the rate, 1/42 = 0.0238 below it.
            (41, 0.0, 1.0, 1 / 41, 1 / 41),
            (42, 0.0, 1.0, 0.024, 0.024),
            (49, 0.0, 0.5, 0.024, 1 / 49),           # was whole under the small-pop rule; 1/49 = 0.0204
            (2, 0.0, 1.0, 0.5, 0.5),
            (0, 0.0, 1.0, 1.0, 1.0),                 # no lower than one person: never above 1
            (1000, 1.0, 0.5, 0.048, 0.024),
            (1000, 40.0, 1.0, 0.5, 0.5),             # the rate's own cap
            (1000, -0.99, 1.0, 0.001, 0.001),        # a tiny rate: one person in a thousand, not the whole pop
        ]
        for size, state_mult, share, step, cross_step in cases:
            with self.subTest(size=size, state_mult=state_mult, share=share):
                world = rate_world(state_mult=state_mult, size=size, cross=share)
                got_step, got_cross = value_in(world, STEP), value_in(world, CROSS_STEP)
                self.assertAlmostEqual(got_step, step)
                self.assertAlmostEqual(got_cross, cross_step)
                self.assertLessEqual(max(got_step, got_cross), 1.0)
        # The cap at 1 as written: the real inputs cannot reach it (the rate is capped at one half, the floor is at
        # most one person in one), so a rate above 1 is stood in for.
        for rate, share, cross_step in ((1.5, 1.0, 1.0), (1.5, 0.5, 0.75), (4.0, 0.5, 1.0)):
            with self.subTest(stood_in_rate=rate, share=share):
                world = rate_world(size=1000, cross=share)
                self.assertAlmostEqual(value_in(world, STEP, values={"te_hc_pop_rate": rate}), 1.0)
                self.assertAlmostEqual(value_in(world, CROSS_STEP, values={"te_hc_pop_rate": rate}), cross_step)


def any_shared(world, country):
    """te_hc_any_shared as the coordinator's fix round 3 defines it (replacing changes note 5): 1 under Hybrid Cultures
    exactly when some culture (a) has people in the country, (b) shares no heritage group with any primary culture of
    the country, and (c) has a homeland in a state the country holds that is also a primary culture's homeland. It
    need not live in that state, and the host's language is not asked. 0 otherwise, and under the other settings.
    The flag test's oracle only: the prune test reads the script's own flag (script_any_shared)."""
    if world.mode != 1:
        return 0
    groups = {world.ents[c].group for c in world.ents[country].primaries}
    shared = world.primary_homelands(country) & {world.ents[s].region for s in world.items(country, "scope_state")}
    living = {world.ents[pid].culture for pid in world.items(country, "scope_pop")}
    for cid in world.items(country, "scope_culture"):
        culture = world.ents[cid]
        if cid in living and culture.group not in groups and culture.homelands & shared:
            return 1
    return 0


def script_any_shared(world):
    """te_hc_any_shared as the script's own te_hc_yearly_country computes it over the world (its state passes stood
    in for)."""
    _, interp = yearly_walk(world)
    return interp.locals["te_hc_any_shared"]


class LocalCultureTest(unittest.TestCase):
    """te_hc_find_locals run on its own in S1 (state scope), the host P, under Hybrid Cultures, with te_hc_any_shared
    as the script's te_hc_yearly_country computes it for the same world."""

    # (the owner's cultures in order, the levels found, the cultures kept)
    CASES = [
        (["C5", "C6", "C3", "C4"], {}, {}),
        (["C5", "C6", "C3", "C4", "C2"], {"african": 1}, {"african": "C2"}),
        (["C5", "C6", "C3", "C4", "C2", "C1", "C8"], {"african": 2, "south_asian": 1},
         {"african": "C1", "south_asian": "C8"}),
        (["C1", "C2"], {"african": 2}, {"african": "C1"}),        # a homeland here is kept over a later one
        (["C2", "C1"], {"african": 2}, {"african": "C1"}),        # and replaces an earlier shared-homeland one
        (["C2", "C2b"], {"african": 1}, {"african": "C2"}),       # otherwise the first found is kept
        (["C7"], {}, {}),                                         # listed, but nobody in the country (note 4)
        (["C7", "C2"], {"african": 1}, {"african": "C2"}),
    ]
    # Cases where a culture's people live elsewhere than the default: (order, homes, levels, kept).
    MOVED = [
        # C2 lives in the country (S4) and shares the held S2 with P as a homeland; nobody of another group lives in
        # S2. Spec line 108: it is S1's local culture all the same (round 2's finding).
        (["C2"], {"C2": "S4"}, {"african": 1}, {"african": "C2"}),
        (["C2"], {"C2": "S3"}, {}, {}),                           # its only people are in OTHER's S3
        (["C3"], {"C3": "S4"}, {}, {}),                           # its homeland shared with P is OTHER's S3
        (["C4", "C2"], {"C2": "S4", "C4": "S2"}, {"african": 1}, {"african": "C2"}),
    ]

    def world(self, order, homes=None, mode=1):
        # Regions: R1 is S1's; the owner holds S2 (a homeland of the primary culture P) and S4 (of none); OTHER
        # holds S3, a homeland of P. C7 would qualify in S1 but its only people are in OTHER's S3: the country lists
        # it (as the engine's every_scope_culture might) with nobody there. `homes` moves a culture's people.
        homes = dict(homes or {})
        w = World(mode=mode)
        w.culture("P", "european", "l_host", homelands={"R2", "R3"})
        cultures = {
            "C1": ("african", "l_host", {"R1"}),        # its homeland is this state: level 2
            "C1b": ("african", "l_host", {"R1"}),
            "C2": ("african", "l_host", {"R2"}),        # shares an owned homeland with P: level 1
            "C2b": ("african", "l_host", {"R2"}),
            "C3": ("african", "l_host", {"R3"}),        # shares a homeland with P, but the owner does not hold it
            "C4": ("african", "l_host", {"R4"}),        # an owned homeland, but not a primary culture's
            "C5": ("african", "l_other", {"R1", "R2"}),  # does not speak the host's language
            "C6": ("european", "l_host", {"R1", "R2"}),  # shares the primary culture's heritage group
            "C7": ("african", "l_host", {"R1"}),
            "C8": ("south_asian", "l_host", {"R2"}),
        }
        for cid, (group, language, homelands) in cultures.items():
            w.culture(cid, group, language, homelands=homelands)
        w.country("OWNER", ["P"], capital="S2", modifiers=country_modifiers(cross=1.0), cultures=["P"] + order)
        w.country("OTHER", [])
        w.state("S1", "OWNER", region="R1")
        w.state("S2", "OWNER", region="R2")
        w.state("S3", "OTHER", region="R3")
        w.state("S4", "OWNER", region="R4")
        # Only C1 and C1b live in S1 itself: the rest of the owner's cultures live elsewhere in the country.
        for cid in order:
            if cid != "C7":
                w.pop(f"P_{cid}", homes.get(cid, "S1" if cid in ("C1", "C1b") else "S2"), cid)
        w.pop("P_C7", "S3", "C7")
        w.pop("P_P", "S1", "P")
        return w

    def find(self, order, stale=0, homes=None, shared=None):
        """te_hc_find_locals in S1. The flag is `shared` where given, else the script's own: te_hc_yearly_country run
        over a copy of the same world."""
        w = self.world(order, homes)
        shared = script_any_shared(self.world(order, homes)) if shared is None else shared
        locals_ = dict(pass_locals(), te_hc_has_host=1, te_hc_has_targets=0, te_hc_any_shared=shared)
        saved = {"te_hc_owner": "OWNER", "te_hc_state": "S1", "te_hc_host": "P"}
        if stale:
            for group in GROUPS:
                locals_[f"te_hc_has_local_{group}"] = stale
                saved[f"te_hc_l_{group}"] = "C7"
        interp = Interp(script(), w, locals_=locals_, saved=saved)
        interp.run_effect("te_hc_find_locals", ["OWNER", "S1"])
        levels = {g: interp.locals.get(f"te_hc_has_local_{g}") for g in GROUPS}
        kept = {g: interp.saved.get(f"te_hc_l_{g}") for g in GROUPS if levels[g]}
        return levels, kept, interp

    def test_a_local_culture_needs_people_language_group_and_a_shared_homeland(self):
        nothing = {g: 0 for g in GROUPS}
        for order, levels, kept in self.CASES:
            with self.subTest(order=order):
                got_levels, got_kept, _ = self.find(order)
                self.assertEqual(got_levels, dict(nothing, **levels))
                self.assertEqual(got_kept, kept)
        # Two whose homeland this state is: one of them, at level 2.
        got_levels, got_kept, _ = self.find(["C1", "C1b"])
        self.assertEqual(got_levels["african"], 2)
        self.assertIn(got_kept["african"], ("C1", "C1b"))
        # The cheap trait tests come before any walk of the owner's (or a culture's homeland) states.
        _, _, interp = self.find(["C5", "C6", "C2"])
        state_walks = [w for w in interp.walks if "state" in w[0] and set(w[3]) & {"C5", "C6"}]
        self.assertEqual(state_walks, [])

    def test_the_shared_homeland_flag_only_prunes_work(self):
        # Changes note 5: te_hc_any_shared lets te_hc_find_locals skip the shared-homeland walk where it cannot
        # succeed; "the meaning of a local culture is unchanged". So each case finds the same with the flag as the
        # country pass sets it and with the flag forced to 1 (no pruning), and that is the case's expected result.
        # The flag is the script's own (te_hc_yearly_country over the same world), not a restatement of it.
        nothing = {g: 0 for g in GROUPS}
        cases = [(order, None, levels, kept) for order, levels, kept in self.CASES] + self.MOVED
        flags = set()
        for order, homes, levels, kept in cases:
            with self.subTest(order=order, homes=homes):
                flags.add(script_any_shared(self.world(order, homes)))
                pruned = self.find(order, homes=homes)[:2]
                unpruned = self.find(order, homes=homes, shared=1)[:2]
                self.assertEqual(unpruned, (dict(nothing, **levels), kept))
                self.assertEqual(pruned, unpruned)
        # Both values occur, so the cases do test the pruning (with the flag at 0 the branch is skipped).
        self.assertEqual(flags, {0, 1})

    def test_the_shared_homeland_flag_is_set_where_a_shared_homeland_holds_another_group(self):
        # te_hc_any_shared, as te_hc_yearly_country sets it (fix round 3's definition): 1 exactly when, under Hybrid
        # Cultures, some culture with people in the country, of no primary culture's heritage group, has a homeland in
        # a state the country holds that is also a homeland of a primary culture (P: R2, R3; the owner holds R1, R2,
        # R4). It need not live in that state; its language is not asked.
        cases = [
            (["C2"], None, 1, 1),               # C2 lives in S2, its homeland and P's
            (["C8"], None, 1, 1),
            (["C5"], None, 1, 1),               # the flag asks no language
            (["C2"], {"C2": "S4"}, 1, 1),       # C2 lives elsewhere in the country; nobody of another group in S2
            (["C2"], {"C2": "S1"}, 1, 1),
            (["C4", "C2"], {"C2": "S4", "C4": "S2"}, 1, 1),
            (["C2"], {"C2": "S3"}, 1, 0),       # listed, but its only people are in OTHER's S3
            (["C3"], {"C3": "S3"}, 1, 0),       # the shared homeland R3 is OTHER's
            (["C3"], None, 1, 0),               # living in the held S2 does not make S2 its homeland
            (["C6"], None, 1, 0),               # C6 shares P's heritage group
            (["C4"], {"C4": "S4"}, 1, 0),       # S4 is C4's homeland but no primary culture's
            (["C4"], {"C4": "S2"}, 1, 0),       # living in P's homeland S2 is not having a homeland there
            (["C1"], None, 1, 0),               # S1 is C1's homeland but no primary culture's
            (["C7"], None, 1, 0),
            (["C2"], None, 2, 0),               # not under Unrestricted
            (["C2"], None, 3, 0),               # nor None
            (["C2"], {"C2": "S4"}, 2, 0),
        ]
        for order, homes, mode, flag in cases:
            with self.subTest(order=order, homes=homes, mode=mode):
                world = self.world(order, homes, mode=mode)
                self.assertEqual(any_shared(world, "OWNER"), flag)
                _, interp = yearly_walk(world)
                self.assertEqual(interp.locals.get("te_hc_any_shared"), flag)

    def test_local_flags_are_reset_in_every_state(self):
        # Review Focus 2: every group's local is cleared in each state before any culture is kept, so a local
        # culture found in an earlier state is never read in this one.
        levels, kept, _ = self.find(["C5", "C3"], stale=2)
        self.assertEqual(levels, {g: 0 for g in GROUPS})
        levels, kept, _ = self.find(["C2"], stale=2)
        self.assertEqual(levels, dict({g: 0 for g in GROUPS}, african=1))
        self.assertEqual(kept, {"african": "C2"})
        # Under Hybrid Cultures each state's pass calls te_hc_find_locals and te_hcg_save_targets, after the host.
        row = dict(mode=1, speaks=False, targets=1, local=0, blocked=0, slave=False, cross=1.0, group="african")
        interp = run_table_world(table_world(row, stale=True), 1.0)
        for sid in ("S0", "S1"):
            names = [name for name, scope in interp.calls if scope == sid]
            for name in ("te_hc_find_locals", "te_hcg_save_targets"):
                self.assertEqual(names.count(name), 1, (sid, name, names))
                self.assertLess(names.index("te_hc_pick_host"), names.index(name), (sid, names))

    def test_the_local_search_names_no_culture(self):
        effects, triggers = script().effects, script().triggers
        text = body_text(EFFECTS, "te_hc_find_locals")
        for name in callees(text, effects) + callees(text, triggers):
            text += " " + (effects.get(name) or triggers.get(name))[1]
        self.assertNotIn("cu:", text)
        self.assertEqual(named_cultures(text), set())


def culture_keys():
    keys = set(vanilla_parsed.load(str(ROOT / "vanilla_parsed")).data["Cultures"])
    for path in sorted((ROOT / "common/cultures").glob("*.txt")):
        keys |= set(re.findall(r"(?m)^(\w+)\s*=\s*\{", code(path)))
    return keys


def named_cultures(text):
    """Culture keys written as a value (right of an operator, or in a list). Keys are left out: `min = 0` is an
    operation, though `min` is also vanilla's Min culture."""
    values = {n.value for n in walk_nodes(parse(text)) if n.value} | \
             {n.key for n in walk_nodes(parse(text)) if n.op is None and n.key}
    return values & culture_keys()


class NamesNoCultureTest(unittest.TestCase):
    def test_the_pass_names_no_culture(self):
        for path in PASS_FILES:
            with self.subTest(path=path.name):
                text = code(path)
                if path == TRIGGERS:
                    # The one literal: the sentinel, in te_hc_mode_hybrid.
                    self.assertEqual(re.findall(r"cu:\w+", text), [f"cu:{cfg.SENTINEL}"])
                    self.assertIn(f"cu:{cfg.SENTINEL}", body_text(TRIGGERS, "te_hc_mode_hybrid"))
                    text = text.replace(f"cu:{cfg.SENTINEL}", "the_sentinel")
                self.assertNotIn("cu:", text)
                self.assertEqual(named_cultures(text), set())


if __name__ == "__main__":
    unittest.main()
