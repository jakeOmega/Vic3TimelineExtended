"""The Extraplanetary Base's ground types in script (ground types design § 5 and § 8).

``scripts/generators/gen_ebase.py`` writes the per-place script from
``scripts/generators/ebase_ground.py``, the model. These tests hold the generated
files to the model two ways:

- by structure: every place, method and good is there, in the order and form the
  rules need (the plan's Task 5 and Task 6 lists);
- by behaviour: ``_Twin`` runs the generated script itself, from the files as they
  are, in the engine's fixed point (values in units of 1e-5, every operation cut
  toward zero, as ``test_space_fleets._Fx``), with fixtures for what the engine
  reads (holders, blockades, room, buildings and their methods, prices), and the
  result is compared with the model's.
"""
from __future__ import annotations

import os
import dataclasses
import random
import re
import sys
import unittest
from decimal import Decimal, InvalidOperation

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import ebase_ground as eg  # noqa: E402
import gen_ebase as ge  # noqa: E402
import gen_solar_sites as gss  # noqa: E402


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"no block {name}")
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[m.end():i - 1]


VALUES = _strip(_raw(str(ge.VALUES_OUT)))
EFFECTS = _strip(_raw(str(ge.EFFECTS_OUT)))
MODULES = _strip(_raw("common", "scripted_effects", "sr_colony_module_effects.txt"))
ON_ACTIONS = _strip(_raw("common", "on_actions", "space_race_on_actions.txt"))
SITES = {s.key: s for s in gss.SITES}
ASTEROID = {"pm_space_mine": 1.0}


# ---------------------------------------------------------------------------
# The twin: the generated script run in the engine's fixed point
# ---------------------------------------------------------------------------

SCALE = 100_000
_TOKEN = re.compile(r'"[^"]*"|#[^\n]*|<=|>=|!=|\?=|[{}=<>]|[^\s{}=<>#"?]+')
_OPS = {"=": lambda a, b: a == b, "?=": lambda a, b: a == b, "!=": lambda a, b: a != b, "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}
FIXED_MAX = 2 ** 63 // SCALE  # about 9.2e13: past it the engine's i64 wraps


def fx(x) -> int:
    """A figure in fixed point."""
    return int(Decimal(repr(x) if isinstance(x, float) else str(x)) * SCALE)


def unfx(v: int) -> float:
    return v / SCALE


def _cut(p, q):
    r = abs(p) // abs(q)
    return r if (p < 0) == (q < 0) else -r


def _tokens(text):
    return [t for t in _TOKEN.findall(text) if not t.startswith("#")]


def _parse(tokens, i=0):
    """[(key, op, value)] up to the matching '}' (value a token or a nested list)."""
    out = []
    while i < len(tokens) and tokens[i] != "}":
        if i + 1 >= len(tokens) or tokens[i + 1] not in _OPS:  # a bare word in a list
            out.append((tokens[i], None, None))
            i += 1
            continue
        key, op = tokens[i], tokens[i + 1]
        if tokens[i + 2] == "{":
            value, i = _parse(tokens, i + 3)
            i += 1
        else:
            value, i = tokens[i + 2], i + 3
        out.append((key, op, value))
    return out, i


def _top_raw(text):
    """Each top-level `name = { ... }` of a file, its body's raw text (for $ARG$)."""
    out, depth, name, start = {}, 0, None, 0
    for m in _TOKEN.finditer(text):
        t = m.group(0)
        if t[0] in '#"':
            continue
        if t == "{":
            start = m.end() if depth == 0 else start
            depth += 1
        elif t == "}":
            depth -= 1
            if depth == 0:
                out[name] = text[start:m.start()]
        elif depth == 0 and t not in _OPS:
            name = t
    return out


class Building:
    """A building fixture: its state, type, level, active methods and the static
    modifiers on it (name -> the multipliers of each copy, so a stack shows)."""

    def __init__(self, state, type_="building_space_mine", level=1, pm="pm_space_mine", mods=None, logistics=()):
        self.state, self.type, self.level = state, type_, level
        self.pms = ({pm} if pm else set()) | set(logistics)
        self.mods: dict[str, list[int]] = {k: [fx(v)] for k, v in (mods or {}).items()}


class Twin:
    """Enough of the engine to run the base's refresh from the files as they are:
    value blocks applied in order (min and max clamp where they stand; inline blocks;
    scope changes to the market and a good), variables, locals and globals, if /
    else_if / else, while (limit or count, the engine's 1,000-pass cap), the state and
    building iterators, modifiers on the country and on buildings, and scripted
    effects and triggers with their $ARG$ substituted as text. Every value is an
    integer of 1e-5 and every operation is cut toward zero (test_space_fleets._Fx's
    model). A read of a variable or local never set fails, as does a variable read in
    building scope (buildings hold none), a removal of a modifier that is not there,
    and a value past the engine's ceiling."""

    _sources = None

    def __init__(self):
        if Twin._sources is None:
            values = {}
            for path in (str(ge.VALUES_OUT),):
                values.update(_top_raw(_raw(path)))
            effects = {}
            for path in (str(ge.EFFECTS_OUT), "common/scripted_effects/sr_colony_module_effects.txt"):
                effects.update(_top_raw(_raw(path)))
            triggers = _top_raw(_raw("common", "scripted_triggers", "sr_site_triggers.txt"))
            sguis = _top_raw(_raw("common", "scripted_guis", "sr_colony_sguis.txt"))
            statics = {}
            for k, v in _top_raw(_raw("common", "static_modifiers", "space_race_modifiers.txt")).items():
                body = _parse(_tokens(v))[0]
                statics[k] = {key: fx(x) for key, _, x in body
                              if isinstance(x, str) and re.fullmatch(r"-?[\d.]+", x)}
            Twin._sources = values, effects, triggers, statics, sguis, {}
        self.values, self.effects, self.triggers, self.statics, self.sguis, self._parsed = Twin._sources
        self.vars: dict[str, int] = {}
        self.locals: dict[str, int] = {}
        self.globals: dict[str, object] = {}
        self.techs: set[str] = set()
        self.rules: set[str] = {"space_race_colonies_simple"}
        self.country_mods: dict[str, list[int]] = {}
        self.buildings: list[Building] = []
        self.market: dict[str, tuple[int, int]] = {}
        self.stub_values: dict[str, int] = {}
        self.stub_effects: dict = {}
        self.scope: list = ["country"]
        self.calls: list[str] = []
        self.logs: list[str] = []
        self.loops: list[int] = []
        # Task 7: a scripted GUI's saved scopes (scope:site, scope:op), whether the country
        # is an AI's, the notifications posted, the tooltip lines shown, and the tooltip
        # walk (`walk`: every limit and value evaluated, nothing written).
        self.saved: dict[str, int] = {}
        self.is_ai = False
        self.notifications: list[str] = []
        self.tooltips: list[str] = []
        self.walk = False
        self.values_read: list[str] = []

    # -- fixtures ------------------------------------------------------------
    def hold(self, place, *, serves=True, occupied=False):
        """We hold `place`; it serves us unless blockaded (or occupied)."""
        if place == eg.NEAR_EARTH:
            self.techs.add(gss.NEAR_EARTH_TECH)
            return
        self.globals[f"sr_site_holder_{place}"] = "THIS"
        if not serves:
            self.globals[f"sr_site_{'occupier' if occupied else 'blockaded'}_{place}"] = "OTHER"

    def room(self, place, levels):
        if place != eg.NEAR_EARTH:
            self.stub_values[f"sr_site_ebase_room_{place}"] = fx(levels)

    def price(self, good, rel):
        """A good's premium: pricier above base price, cheaper below (both read >= 0,
        the clamped hypothesis; the values build the signed premium either way)."""
        r = fx(round(rel, 5))
        self.market[good] = (max(r, 0), max(-r, 0))

    # -- values --------------------------------------------------------------
    def _value_block(self, name):
        key = ("value", name)
        if key not in self._parsed:
            self._parsed[key] = _parse(_tokens(self.values[name]))[0]
        return self._parsed[key]

    def num(self, v):
        if isinstance(v, list):
            return self.calc(v)
        where = self.scope[-1]
        if v.startswith("var:"):
            assert where == "country", f"{v} read in {where}: buildings hold no variables"
            assert v[4:] in self.vars, f"{v} read, never set"
            return self.vars[v[4:]]
        if v.startswith("root.var:"):
            assert v[9:] in self.vars, f"{v} read, never set"
            return self.vars[v[9:]]
        if v.startswith("local_var:"):
            assert v[10:] in self.locals, f"{v} read, never set"
            return self.locals[v[10:]]
        if v.startswith("scope:"):
            assert v[6:] in self.saved, f"{v} read, never saved"
            return self.saved[v[6:]]
        if v.startswith("global_var:"):
            value = self.globals[v[11:]]
            assert isinstance(value, int), f"{v} is not a number"
            return value
        if v.startswith("modifier:"):
            assert isinstance(where, Building), f"{v} read outside a building"
            field = v[9:]
            return sum(_cut(self.statics[m].get(field, 0) * mult, SCALE)
                       for m, copies in where.mods.items() for mult in copies)
        if v == "level":
            assert isinstance(where, Building)
            return fx(where.level)
        if v in ("market_goods_pricier", "market_goods_cheaper"):
            assert isinstance(where, tuple) and where[0] == "mg", f"{v} read outside a good's market"
            return self.market.get(where[1], (0, 0))[v == "market_goods_cheaper"]
        if v in self.stub_values:
            return self.stub_values[v]
        if v in self.values:
            self.values_read.append(v)
            return self.calc(self._value_block(v))
        try:
            return fx(v)
        except InvalidOperation:
            raise AssertionError(f"no value {v}") from None

    def calc(self, block, acc=0):
        taken = False
        for key, _, v in block:
            if key in ("if", "else_if", "else"):
                taken = False if key == "if" else taken
                if taken or (key != "else" and not self.test(next(x for k, _, x in v if k == "limit"))):
                    continue
                taken = True
                acc = self.calc([e for e in v if e[0] != "limit"], acc)
            elif key == "market":
                self.scope.append("market")
                acc = self.calc(v, acc)
                self.scope.pop()
            elif key.startswith("mg:"):
                assert self.scope[-1] == "market"
                self.scope.append(("mg", key[3:]))
                acc = self.calc(v, acc)
                self.scope.pop()
            elif key == "ceiling":
                q, r = divmod(acc, SCALE)
                acc = (q + (r > 0)) * SCALE
            elif key == "floor":
                acc = (acc // SCALE) * SCALE
            else:
                x = self.num(v)
                if key == "value":
                    acc = x
                elif key == "add":
                    acc += x
                elif key == "subtract":
                    acc -= x
                elif key == "multiply":
                    acc = _cut(acc * x, SCALE)
                elif key == "divide":
                    assert x != 0, "a division by zero"
                    acc = _cut(acc * SCALE, x)
                elif key == "min":
                    acc = max(acc, x)
                elif key == "max":
                    acc = min(acc, x)
                else:
                    raise AssertionError(f"unsupported value step {key}")
            assert abs(acc) < FIXED_MAX * SCALE, "a value past the engine's ceiling"
        return acc

    # -- triggers ------------------------------------------------------------
    def _body(self, table, name, args):
        given = {} if args == "yes" else {k: x for k, _, x in args}
        raw = table[name]
        for k, x in given.items():
            assert isinstance(x, str), f"{name}: argument {k} is a block"
            assert f"${k}$" in raw, f"{name} doesn't name ${k}$"
            raw = raw.replace(f"${k}$", x)
        key = (id(table), name, tuple(sorted(given.items())))
        if key not in self._parsed:
            tokens = _tokens(raw)
            assert not [t for t in tokens if "$" in t and not t.startswith('"')], f"{name}: an argument missing"
            self._parsed[key] = _parse(tokens)[0]
        return self._parsed[key]

    def test(self, block):
        taken = False
        for key, op, v in block:
            if key in ("trigger_if", "trigger_else_if", "trigger_else"):
                taken = False if key == "trigger_if" else taken
                if taken or (key != "trigger_else" and not self.test(next(x for k, _, x in v if k == "limit"))):
                    continue
                taken = True
                if not self.test([e for e in v if e[0] != "limit"]):
                    return False
            elif not self.cond(key, op, v):
                return False
        return True

    def _buildings(self, block):
        state = self.scope[-1]
        pool = self.buildings if state == "country" else [b for b in self.buildings if b.state == state[1]]
        out = []
        for b in pool:
            self.scope.append(b)
            ok = self.test(block)
            self.scope.pop()
            if ok:
                out.append(b)
        return out

    def cond(self, key, op, v):
        where = self.scope[-1]
        if key == "OR":
            return any(self.cond(*c) for c in v)
        if key == "AND":
            return self.test(v)
        if key == "NOT":
            assert len(v) == 1, "NOT over more than one trigger"
            return not self.cond(*v[0])
        if key == "is_ai":
            return self.is_ai == (v == "yes")
        if key == "always":
            return v == "yes"
        if key == "custom_tooltip":
            return self.test([e for e in v if e[0] != "text"]) if isinstance(v, list) else True
        if key == "has_variable":
            assert where == "country", "has_variable in a building: buildings hold no variables"
            return v in self.vars
        if key == "has_global_variable":
            return v in self.globals
        if key == "has_technology_researched":
            return v in self.techs
        if key == "has_game_rule":
            return v in self.rules
        if key == "has_modifier":
            mods = where.mods if isinstance(where, Building) else self.country_mods
            return bool(mods.get(v))
        if key == "is_building_type":
            return where.type == v
        if key == "has_active_production_method":
            return v in where.pms
        if key == "any_scope_building":
            return bool(self._buildings(v))
        if key in self.triggers:
            if v in ("yes", "no"):
                return self.test(self._body(self.triggers, key, "yes")) == (v == "yes")
            return self.test(self._body(self.triggers, key, v))
        if key.startswith("global_var:") and v == "this":
            assert op == "?=", f"{key} = this without ?="
            return self.globals.get(key[11:]) == "THIS"
        return _OPS[op](self.num(key), self.num(v))

    # -- effects -------------------------------------------------------------
    def _mods(self):
        where = self.scope[-1]
        return where.mods if isinstance(where, Building) else self.country_mods

    def run(self, block):
        taken = False
        for key, _, v in block:
            if key in ("if", "else_if", "else"):
                taken = False if key == "if" else taken
                if taken or (key != "else" and not self.test(next(x for k, _, x in v if k == "limit"))):
                    continue
                taken = True
                self.run([e for e in v if e[0] != "limit"])
            elif key == "while":
                body = [e for e in v if e[0] not in ("limit", "count")]
                limit = next((x for k, _, x in v if k == "limit"), None)
                count = next((x for k, _, x in v if k == "count"), None)
                passes = 0
                while passes < 1000 and (limit is None or self.test(limit)) and (
                        count is None or passes < _cut(self.num(count), SCALE)):
                    self.run(body)
                    passes += 1
                assert passes < 1000, "a while ran to the engine's cap"
                self.loops.append(passes)
            elif key in ("set_variable", "set_local_variable"):
                d = {k: x for k, _, x in v} if isinstance(v, list) else {"name": v}
                assert self.scope[-1] == "country" or key == "set_local_variable", \
                    f"{key} in {self.scope[-1]}: buildings hold no variables"
                value = SCALE if d.get("value", "yes") == "yes" else self.num(d["value"])
                if not self.walk:
                    (self.locals if key == "set_local_variable" else self.vars)[d["name"]] = value
            elif key in ("change_variable", "change_local_variable"):
                d = {k: x for k, _, x in v}
                store = self.locals if key == "change_local_variable" else self.vars
                assert set(d) <= {"name", "add", "subtract"}, f"{key} with {set(d)}"
                change = self.num(d["add"]) if "add" in d else -self.num(d["subtract"])
                if not self.walk:
                    assert d["name"] in store, f"{key} on {d['name']}, never set"
                    store[d["name"]] += change
            elif key == "remove_variable":
                if not self.walk:
                    assert v in self.vars, f"remove_variable {v}, not set"
                    del self.vars[v]
            elif key == "custom_tooltip":
                self.tooltips.append(v if isinstance(v, str) else next(x for k, _, x in v if k == "text"))
                if isinstance(v, list):
                    self.run([e for e in v if e[0] != "text"])
            elif key == "post_notification":
                if not self.walk:
                    self.notifications.append(v)
            elif key == "set_global_variable":
                d = {k: x for k, _, x in v} if isinstance(v, list) else {"name": v}
                self.globals[d["name"]] = SCALE if d.get("value", "yes") == "yes" else self.num(d["value"])
            elif key == "add_modifier":
                d = {k: x for k, _, x in v} if isinstance(v, list) else {"name": v}
                mult = self.num(d["multiplier"]) if "multiplier" in d else SCALE
                if not self.walk:
                    self._mods().setdefault(d["name"], []).append(mult)
            elif key == "remove_modifier" and self.walk:
                pass
            elif key == "remove_modifier":
                mods = self._mods()
                assert mods.get(v), f"remove_modifier {v}, not there"
                del mods[v]
            elif key == "every_scope_state":
                assert self.scope[-1] == "country"
                for state in sorted({b.state for b in self.buildings}):
                    self.scope.append(("state", state))
                    self.run(v)
                    self.scope.pop()
            elif key in ("every_scope_building", "random_scope_building"):
                limit = next((x for k, _, x in v if k == "limit"), [])
                hits = self._buildings(limit)
                for b in hits[:1] if key == "random_scope_building" else hits:
                    self.scope.append(b)
                    self.run([e for e in v if e[0] != "limit"])
                    self.scope.pop()
            elif key == "debug_log":
                for name_ in re.findall(r"THIS\.Var\('(\w+)'\)", v):
                    assert name_ in self.vars, f"the line reads {name_}, never set"
                self.logs.append(v)
            elif key in self.stub_effects:
                self.calls.append(key)
                self.stub_effects[key](self)
            elif key in self.effects:
                self.calls.append(key)
                self.run(self._body(self.effects, key, v))
            else:
                raise AssertionError(f"unsupported effect {key}")

    def effect(self, name):
        self.run([(name, "=", "yes")])

    def _sgui(self, name, part):
        key = ("sgui", name)
        if key not in self._parsed:
            self._parsed[key] = _parse(_tokens(self.sguis[name]))[0]
        return next(v for k, _, v in self._parsed[key] if k == part)

    def click(self, name, *, walk=False, **saved):
        """A scripted GUI's effect, run on a click (or, with `walk`, walked for its
        tooltip as the engine does each frame of a hover: nothing written)."""
        self.saved = {k: fx(v) for k, v in saved.items()}
        self.walk = walk
        try:
            self.run(self._sgui(name, "effect"))
        finally:
            self.walk = False

    def valid(self, name, **saved):
        self.saved = {k: fx(v) for k, v in saved.items()}
        return self.test(self._sgui(name, "is_valid"))

    def shown(self, name):
        return self.test(self._sgui(name, "is_shown"))

    # -- reading back ---------------------------------------------------------
    def counts(self, prefix):
        return {p: unfx(self.vars[f"{prefix}{p}"]) for p in eg.PLACES if f"{prefix}{p}" in self.vars}


def _twin_base(at=None, *, built, rooms, serving=None, blockaded=(), lost=(), queued=None):
    """A twin for a country with In-Situ Resource Utilization holding the places in
    `rooms` (place -> room), each serving unless blockaded; `lost` places are on record
    and no longer held."""
    tw = Twin()
    tw.techs.add("in_situ_resource_utilization")
    for p, r in rooms.items():
        if p in lost:
            continue
        tw.hold(p, serves=p not in blockaded)
        tw.room(p, r)
    for s in gss.SITES:
        tw.stub_values.setdefault(f"sr_site_ebase_room_{s.key}", 0)
    tw.stub_values["sr_ebase_levels"] = fx(built)
    tw.stub_values["sr_ebase_queued_levels"] = fx(built if queued is None else queued)
    tw.stub_values["sr_ebase_room_total"] = fx(sum(r for p, r in rooms.items() if p not in lost and p not in blockaded))
    tw.stub_values["te_history_month_index"] = fx(24000)
    for p, n in (at or {}).items():
        tw.vars[f"sr_eb_at_{p}"] = fx(n)
    return tw


# ---------------------------------------------------------------------------
# Task 5: the generated values, the two layers on today's order, the refresh
# ---------------------------------------------------------------------------

class GeneratedFilesTest(unittest.TestCase):
    def test_outputs_are_current(self):
        result = ge.regenerate(dry_run=True)
        self.assertEqual(result["changed_files"], [], "run python3 scripts/generators/gen_ebase.py")

    def test_one_bom_and_the_header(self):
        for path in ge.plan_outputs():
            with self.subTest(path=str(path)):
                data = open(os.path.join(REPO, path), "rb").read()
                self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(data[3:].startswith(b"\xef\xbb\xbf"))
                self.assertTrue(data[3:].decode("utf-8").startswith(ge.HEADER))

    def test_registered_after_gen_solar_sites(self):
        post_load = _raw("server", "post_load.py")
        roster = re.findall(r'\("(\w+)",\s+"[\w.]+"\)', post_load)
        self.assertEqual(roster[roster.index("gen_solar_sites") + 1], "gen_ebase")
        self.assertIn('"scripts.generators.gen_ebase"', post_load)
        owners = _raw("docs", "auto_generated_files.md")
        nightly = _raw("scripts", "nightly_audit_select.py")
        for path in ge.plan_outputs():
            with self.subTest(path=str(path)):
                self.assertIn(f"`{path}`", owners)
                self.assertIn(f'"{path}"', nightly)


class ValuesTest(unittest.TestCase):
    """The plan's Task 5 values, one for each place, method and good."""

    def test_every_place_has_room_grade_and_profit_values(self):
        for i, k in ge.places():
            with self.subTest(place=k):
                room = _block(VALUES, f"sr_eb_room_{k}")
                self.assertIn(f"if = {{ limit = {{ {ge.serves(k)} }} value = {ge.room_value(k)} }}", room)
                self.assertEqual(_block(VALUES, f"sr_eb_grade_{k}").strip(), f"value = {ge.grade_pct(k)}")
                self.assertIn(f"value = sr_eb_margin_{eg.GROUND[k]} multiply = {100 + ge.grade_pct(k)} divide = 100",
                              _block(VALUES, f"sr_eb_profit_{k}"))
        self.assertEqual(len(ge.places()), 41)
        self.assertEqual(ge.serves("near_earth"), f"has_technology_researched = {gss.NEAR_EARTH_TECH}")
        self.assertEqual(ge.room_value("near_earth"), str(gss.NEAR_EARTH_ROOM))
        for s in gss.SITES:
            self.assertEqual(ge.serves(s.key), gss.site_serves(s))

    def test_margins_name_every_mining_method(self):
        """Every mining method, and no other (the Resort Colony's goods are outside
        the seven: shared brief, 2026-11-21)."""
        mining = set(eg.mining_methods())
        for t in eg.TYPES:
            with self.subTest(type=t):
                body = _block(VALUES, f"sr_eb_margin_{t}")
                named = set(re.findall(r"multiply = sr_eb_levels_(\w+?)(?:_in_\w+)? }", body))
                self.assertEqual(named, mining)
                # A cut input reads the method's levels weighted by the cuts.
                for pm in mining:
                    for g in eg.cut_goods():
                        self.assertEqual(f"multiply = sr_eb_levels_{pm}_in_{g} }}" in body,
                                         g in eg.mining_methods()[pm].inputs)
                # Multiplied by each method's levels, divided once by all of them.
                self.assertTrue(body.rstrip().endswith("divide = sr_eb_mining_divisor"))
        for pm in eg.base_methods():
            with self.subTest(pm=pm):
                self.assertEqual(f"sr_eb_share_{pm} = {{" in VALUES, pm in mining)

    def test_margin_constants_match_the_model(self):
        for t in eg.TYPES:
            body = _block(VALUES, f"sr_eb_margin_{t}")
            for pm in eg.mining_methods():
                with self.subTest(type=t, pm=pm):
                    terms = re.findall(rf"add = 1 multiply = (-?[\d.]+) multiply = sr_eb_levels_{pm}(?:_in_\w+)? }}",
                                       body)
                    self.assertAlmostEqual(sum(map(float, terms)), eg.margin(t, {pm: 1.0}, {}), delta=0.01)

    def test_every_good_has_a_signed_premium(self):
        for g in eg.method_goods():
            with self.subTest(good=g):
                self.assertIn(f"mg:{g} = {{ add = market_goods_pricier }}", _block(VALUES, f"sr_eb_price_up_{g}"))
                self.assertIn(f"mg:{g} = {{ add = market_goods_cheaper }}", _block(VALUES, f"sr_eb_price_down_{g}"))
                self.assertIn("min = 0", _block(VALUES, f"sr_eb_price_down_{g}"))
                self.assertEqual(_block(VALUES, f"sr_eb_price_rel_{g}").strip(),
                                 f"value = sr_eb_price_up_{g} subtract = sr_eb_price_down_{g}")

    def test_pace_and_yardstick(self):
        self.assertEqual(_block(VALUES, "sr_eb_pace").strip(),
                         f"value = sr_ebase_levels divide = {eg.PACE_MONTHS} ceiling = yes min = 1")
        yard = _block(VALUES, "sr_eb_yardstick")
        for pm in eg.mining_methods():
            with self.subTest(pm=pm):
                terms = re.findall(rf"add = {{ value = sr_eb_levels_{pm}(?:_in_\w+)? multiply = (-?[\d.]+) }}", yard)
                self.assertAlmostEqual(sum(map(float, terms)), eg.margin("mixed", {pm: 1.0}, {}), delta=0.01)
        self.assertTrue(yard.rstrip().endswith("divide = sr_eb_mining_divisor"))

    def test_profit_runs_the_model_at_market_prices(self):
        """The generated profit a level, run in fixed point from the market's reads and
        the method counts, against the model's profit_a_level, within £0.05."""
        rng = random.Random(1397)
        for trial in range(12):
            tw = Twin()
            levels = {pm: rng.choice((0, 0, 3, 10, 40)) for pm in eg.mining_methods()}
            if not sum(levels.values()):
                levels["pm_space_mine"] = 5
            fleet = []   # (method, levels, logistics): two buildings a method, each on its own cuts
            for pm, lv in levels.items():
                if lv:
                    fleet += [(pm, lv, tuple(c for c in eg.input_cuts() if rng.random() < 0.5)),
                              (pm, rng.choice((1, 6)), tuple(c for c in eg.input_cuts() if rng.random() < 0.5))]
            for n, (pm, lv, logistics) in enumerate(fleet):
                tw.buildings.append(Building(n, level=lv, pm=pm, logistics=logistics))
            tw.buildings.append(Building(9, level=7, pm="pm_space_colony_vacation",  # outside the seven goods
                                         logistics=tuple(eg.input_cuts())))
            prices = {g: rng.uniform(-0.75, 1.5) for g in eg.method_goods()}
            for g, r in prices.items():
                tw.price(g, r)
            tw.effect("sr_eb_count_methods")
            total = sum(lv for _, lv, _ in fleet)
            shares = {pm: sum(lv for m, lv, _ in fleet if m == pm) / total for pm in levels if levels[pm]}
            cuts = eg.method_cuts(fleet)
            rel = {g: round(r, 5) for g, r in prices.items()}
            for k in ("near_earth", "psyche", "ceres", "io", "titan", "ganymede", "vesta", "sedna"):
                with self.subTest(trial=trial, place=k):
                    self.assertAlmostEqual(unfx(tw.num(f"sr_eb_profit_{k}")), eg.profit_a_level(k, shares, rel, cuts),
                                           delta=0.05)
            self.assertAlmostEqual(unfx(tw.num("sr_eb_yardstick")), eg.yardstick(shares, cuts), delta=0.05)
        # No mining level at all: every share, margin and the yardstick read 0.
        tw = Twin()
        tw.effect("sr_eb_count_methods")
        self.assertEqual((tw.num("sr_eb_yardstick"), tw.num("sr_eb_profit_psyche")), (0, 0))

    def test_premium_is_signed_either_way(self):
        """The premium is right whether the engine clamps the two reads at zero or
        mirrors them (scripting_best_practices.md, "Is it signed below base price?")."""
        tw = Twin()
        for pricier, cheaper, want in ((0.4, 0, 0.4), (0, 0.3, -0.3), (0.4, -0.4, 0.4), (-0.3, 0.3, -0.3)):
            with self.subTest(pricier=pricier, cheaper=cheaper):
                tw.market["glass"] = (fx(pricier), fx(cheaper))
                self.assertEqual(tw.num("sr_eb_price_rel_glass"), fx(want))

    def test_pace(self):
        tw = Twin()
        for levels in (0, 1, 47, 48, 49, 96, 150, 1000):
            with self.subTest(levels=levels):
                tw.stub_values["sr_ebase_levels"] = fx(levels)
                self.assertEqual(tw.num("sr_eb_pace"), fx(eg.pace(levels)))


class RefreshTest(unittest.TestCase):
    """The refresh (§ 5.3, § 8.8): strip once, then the two layers under the rule with
    the technology; strip only otherwise, the counts left as they are."""

    def setUp(self):
        self.refresh = _block(MODULES, "sr_ebase_refresh")

    def test_refresh_removes_before_it_adds(self):
        r = self.refresh
        self.assertLess(r.index("sr_eb_strip_mix = yes"), r.index("sr_eb_apply_mix = yes"))
        self.assertEqual(r.count("sr_eb_strip_mix = yes"), 1)
        self.assertEqual(r.count("sr_eb_apply_mix = yes"), 1)
        self.assertLess(r.index("remove_modifier = sr_ebase_room_bonus"), r.index("add_modifier"))
        self.assertLess(r.index("remove_modifier = sr_ebase_room_penalty"), r.index("add_modifier"))
        self.assertLess(r.index("sr_eb_mix_self_check = yes"), r.index("sr_eb_strip_mix = yes"))
        strip = _block(EFFECTS, "sr_eb_strip_mix")
        apply = _block(EFFECTS, "sr_eb_apply_mix")
        self.assertNotIn("remove_modifier", apply)
        self.assertNotIn("add_modifier", strip)
        for g in eg.GOODS:
            for side in ("bonus", "penalty"):
                with self.subTest(good=g, side=side):
                    m = f"sr_ebase_mix_{g}_{side}"
                    self.assertIn(f"if = {{ limit = {{ has_modifier = {m} }} remove_modifier = {m} }}", strip)
                    self.assertIn(f"add_modifier = {{ name = {m} multiplier = root.var:sr_ebase_mix_{g}_units }}", apply)

    def test_gate_reaches_captured_bases(self):
        gate = ON_ACTIONS[ON_ACTIONS.index("space_race_on_action = {"):]
        gate = gate[:gate.index("sr_ebase_refresh = yes")]
        self.assertRegex(gate, r"OR = \{\s*has_technology_researched = in_situ_resource_utilization\s*"
                               r"any_scope_building = \{ is_building_type = building_space_mine \}\s*\}\s*\}\s*$")
        # Without the technology the refresh only strips.
        guarded = self.refresh[self.refresh.index("sr_colonies_contested_enabled = yes"):]
        self.assertIn("has_technology_researched = in_situ_resource_utilization", guarded[:200])
        for call in ("sr_eb_count_methods", "sr_eb_month", "sr_eb_compute_mix", "sr_eb_apply_mix", "sr_eb_next_place"):
            with self.subTest(call=call):
                self.assertGreater(self.refresh.index(f"{call} = yes"), self.refresh.index("sr_colonies_contested_enabled = yes"))

    def _captured(self, *, tech, rules=("space_race_colonies_simple",)):
        tw = _twin_base({"psyche": 40}, built=60, rooms={"psyche": 300})
        tw.rules = set(rules)
        if not tech:
            tw.techs.discard("in_situ_resource_utilization")
        tw.vars["sr_eb_over"] = fx(20)
        # Two bases, one carrying an old owner's mix and a stale copy of our own.
        tw.buildings = [Building(1, level=40, mods={"sr_ebase_mix_glass_penalty": 91, "sr_ebase_mix_gold_bonus": 30}),
                        Building(2, level=20, mods={"sr_ebase_mix_sulfur_bonus": 320})]
        tw.globals["sr_eb_mix_checked"] = SCALE
        tw.effect("sr_ebase_refresh")
        return tw

    def test_captured_base_without_the_technology_is_stripped(self):
        tw = self._captured(tech=False)
        self.assertEqual([b.mods for b in tw.buildings], [{}, {}])
        self.assertEqual((tw.counts("sr_eb_at_"), unfx(tw.vars["sr_eb_over"])), ({"psyche": 40}, 20))

    def test_races_only_strips(self):
        """Races Only, or the rule switched off mid-game: strip, add none, and keep the
        counts in their variables (§ 8.8: the rule switched off pauses)."""
        tw = self._captured(tech=True, rules=())
        self.assertEqual([b.mods for b in tw.buildings], [{}, {}])
        self.assertEqual(tw.country_mods, {})
        self.assertEqual((tw.counts("sr_eb_at_"), unfx(tw.vars["sr_eb_over"])), ({"psyche": 40}, 20))

    def test_the_rule_on_applies_one_copy_a_good(self):
        tw = self._captured(tech=True)
        model = eg.BaseState(at={"psyche": 60})
        _, d = eg.mix_now(model)
        for b in tw.buildings:
            for g in eg.GOODS:
                with self.subTest(building=b.state, good=g):
                    side = "bonus" if d[g] > 0 else "penalty"
                    copies = b.mods.get(f"sr_ebase_mix_{g}_{side}", [])
                    self.assertEqual(len(copies), 1)
                    self.assertAlmostEqual(unfx(copies[0]), abs(d[g]) * 100, delta=1e-3)
                    other = "penalty" if side == "bonus" else "bonus"
                    self.assertNotIn(f"sr_ebase_mix_{g}_{other}", b.mods)
        self.assertEqual(list(tw.country_mods), ["sr_ebase_room_bonus"])
        self.assertAlmostEqual(unfx(tw.country_mods["sr_ebase_room_bonus"][0]), 30, delta=1e-4)

    def test_twice_in_a_day_stacks_nothing(self):
        tw = self._captured(tech=True)
        tw.vars.pop("sr_eb_mix_fresh")
        tw.effect("sr_ebase_refresh")
        for b in tw.buildings:
            self.assertTrue(all(len(c) == 1 for c in b.mods.values()), b.mods)
        self.assertTrue(all(len(c) == 1 for c in tw.country_mods.values()))


class MixTest(unittest.TestCase):
    """§ 5.2: T and D(g) from where the levels work are the model's mix_now, run from a
    first month (every level placed by grade at base prices)."""

    def _first(self, rooms, built, blockaded=()):
        serves = {p: p not in blockaded for p in rooms}
        tw = _month_twin(eg.BaseState(), room=rooms, serves=serves, held={p: True for p in rooms}, built=built,
                         profit={}, yard=YARD)
        tw.effect("sr_eb_month")
        tw.effect("sr_eb_compute_mix")
        return tw

    def test_mix_matches_the_model(self):
        rng = random.Random(5)
        cases = [({"psyche": 300, "ceres": 200}, 150, ()), ({"psyche": 300, "ceres": 200}, 650, ()),
                 ({"near_earth": 10, "titan": 100, "io": 100}, 150, ("io",)), ({}, 20, ())]
        for _ in range(20):
            sites = rng.sample(eg.PLACES, rng.randint(1, 8))
            rooms = {p: (10 if p == "near_earth" else rng.choice((50, 100, 200))) for p in sites}
            blockaded = tuple(p for p in sites if p != "near_earth" and rng.random() < 0.2)
            cases.append((rooms, rng.randint(0, 900), blockaded))
        for rooms, built, blockaded in cases:
            with self.subTest(rooms=rooms, built=built, blockaded=blockaded):
                tw = self._first(rooms, built, blockaded)
                serves = {p: p not in blockaded for p in rooms}
                state = eg.month(eg.BaseState(), room=rooms, serves=serves, held={p: True for p in rooms},
                                 built=built, profit={}, yard=YARD)
                self.assertEqual(_state_of(tw), state)
                t, d = eg.mix_now(state)
                self.assertAlmostEqual(unfx(tw.vars["sr_ebase_grade"]), 100 * t, delta=1e-4)
                for g in eg.GOODS:
                    self.assertAlmostEqual(unfx(tw.vars[f"sr_ebase_mix_{g}"]), 100 * d[g], delta=2e-4, msg=g)
                    self.assertEqual(tw.vars[f"sr_ebase_mix_{g}_units"], abs(tw.vars[f"sr_ebase_mix_{g}"]))

    def test_one_type_base_carries_the_type_mix(self):
        tw = self._first({"vesta": 100, "valles_marineris": 50, "daedalus": 30, "mercury": 7}, 187)
        for g in eg.GOODS:
            with self.subTest(good=g):
                self.assertAlmostEqual(unfx(tw.vars[f"sr_ebase_mix_{g}"]), 100 * eg.mix("rocky")[g], delta=2e-4)

    def test_no_levels_no_mix(self):
        tw = self._first({"psyche": 300}, 0)
        self.assertEqual(tw.vars["sr_ebase_grade"], 0)
        self.assertEqual({g: tw.vars[f"sr_ebase_mix_{g}"] for g in eg.GOODS}, {g: 0 for g in eg.GOODS})

    def test_levels_past_the_room_count_at_minus_75_as_mixed(self):
        """Review focus 1: every place full, the rest at -75% and Mixed."""
        tw = self._first({"psyche": 300, "ceres": 200}, 600)
        state = eg.BaseState(at={"psyche": 300, "ceres": 200}, over=100, placed=True)
        self.assertEqual(_state_of(tw), state)
        t, d = eg.mix_now(state)
        self.assertAlmostEqual(unfx(tw.vars["sr_ebase_grade"]), 100 * t, delta=1e-4)
        for g in eg.GOODS:
            self.assertAlmostEqual(unfx(tw.vars[f"sr_ebase_mix_{g}"]), 100 * d[g], delta=2e-4, msg=g)


# ---------------------------------------------------------------------------
# Task 6: where the levels work, in script, against ebase_ground.month
# ---------------------------------------------------------------------------

TWO_SITES = {"psyche": 300, "ceres": 200}
BOTH = {"psyche": True, "ceres": True}
SKETCH = {"psyche": 9594, "ceres": 11835}
YARD = 7250


def _state(at, **kw):
    return eg.BaseState(at=dict(at), placed=True, **kw)


def _norm(room, serves, held):
    """The model's inputs as the script can have them: the near-Earth asteroids are held
    and serve together (Asteroid Mining) with 10 levels of room."""
    held = dict(serves if held is None else held)
    room, serves = dict(room), dict(serves)
    ne = bool(serves.get(eg.NEAR_EARTH) or held.get(eg.NEAR_EARTH))
    serves[eg.NEAR_EARTH] = held[eg.NEAR_EARTH] = ne
    room[eg.NEAR_EARTH] = gss.NEAR_EARTH_ROOM if ne else 0
    return room, serves, held


def _month_twin(state, *, room, serves, held=None, built, profit, yard, queued=0, month_index=24000, vars_=None):
    """A twin of a country with In-Situ Resource Utilization and this record (or, with
    `vars_`, the variables a previous twin left), the engine's reads fixed to the
    arguments. Profits are fixed through sr_eb_read_profits, which sets exactly the
    locals the real one does (MonthStructureTest holds them in step); the real one is
    run against the model in ValuesTest."""
    room, serves, held = _norm(room, serves, held)
    tw = Twin()
    tw.techs.add("in_situ_resource_utilization")
    if serves[eg.NEAR_EARTH]:
        tw.techs.add(gss.NEAR_EARTH_TECH)
    for s in gss.SITES:
        k = s.key
        tw.stub_values[f"sr_site_ebase_room_{k}"] = fx(room.get(k, 0))
        if held.get(k):
            tw.globals[f"sr_site_holder_{k}"] = "THIS"
            if not serves.get(k):
                tw.globals[f"sr_site_blockaded_{k}"] = "OTHER"
    tw.stub_values["sr_ebase_levels"] = fx(built)
    tw.stub_values["sr_ebase_queued_levels"] = fx(built + queued)
    tw.stub_values["te_history_month_index"] = fx(month_index)
    fixed = {k: fx(round(profit.get(k, 0.0), 5)) for k in eg.PLACES}

    def read_profits(t):
        for k in eg.PLACES:
            t.locals[f"sr_ebi_p_{k}"] = fixed[k]
        for type_ in eg.TYPES:
            t.locals[f"sr_ebi_m_{type_}"] = 0
        t.locals["sr_ebi_yard"] = fx(yard)
        t.locals["sr_ebi_margin"] = _cut(fx(yard) * fx(ge.num(eg.MARGIN)), SCALE)
        t.locals["sr_ebi_p_over"] = 0

    tw.stub_effects["sr_eb_read_profits"] = read_profits
    if vars_ is not None:
        tw.vars = dict(vars_)
    else:
        for prefix, counts in (("sr_eb_at_", state.at), ("sr_eb_target_", state.target), ("sr_eb_away_", state.away)):
            for p, n in counts.items():
                if n:
                    tw.vars[f"{prefix}{p}"] = fx(n)
        if state.over:
            tw.vars["sr_eb_over"] = fx(state.over)
        if state.manual:
            tw.vars["sr_eb_manual"] = SCALE
        if state.placed:
            tw.vars["sr_eb_placed"] = SCALE
    tw.model_inputs = dict(room=room, serves=serves, held=held, built=built,
                           profit={k: unfx(v) for k, v in fixed.items()}, yard=yard)
    return tw


def _state_of(tw):
    """The twin's record as a BaseState (moves left out); every count a whole level."""
    for name_, v in tw.vars.items():
        if name_.startswith(("sr_eb_at_", "sr_eb_target_", "sr_eb_away_", "sr_eb_over")):
            assert v % SCALE == 0, f"{name_} = {unfx(v)}: a fraction of a level"
    as_int = {k: int(v) for k, v in tw.counts("sr_eb_at_").items()}
    return eg.BaseState(at=as_int, target={k: int(v) for k, v in tw.counts("sr_eb_target_").items()},
                        away={k: int(v) for k, v in tw.counts("sr_eb_away_").items()},
                        over=int(unfx(tw.vars.get("sr_eb_over", 0))), manual="sr_eb_manual" in tw.vars,
                        placed="sr_eb_placed" in tw.vars)


def _model(state, tw):
    s = eg.month(state, **tw.model_inputs)
    return s


class MonthTwinTest(unittest.TestCase):
    """The generated sr_eb_month, run in the twin, does what ebase_ground.month does on
    test_ebase_ground.Month's scenarios and the review focus's: the same at, target,
    away, over and placed, month after month."""

    def check(self, state, **kw):
        tw = _month_twin(state, **kw)
        tw.effect("sr_eb_month")
        want = _model(state, tw)
        got = _state_of(tw)
        want_cmp = eg.BaseState(at=want.at, target=want.target, away=want.away, over=want.over,
                                manual=want.manual, placed=want.placed)
        self.assertEqual(got, want_cmp)
        self.assertTrue(all(n <= ge.MONTH_PASSES for n in tw.loops), tw.loops)
        return got, want, tw

    def test_first_month_places_everything_at_once(self):
        got, _, _ = self.check(eg.BaseState(), room=TWO_SITES, serves=BOTH, built=150,
                               profit=eg.profits(ASTEROID, {}), yard=YARD)
        self.assertEqual((got.at, got.placed), ({"psyche": 150}, True))

    def test_checkbox_moves_at_the_pace(self):
        got, _, tw = self.check(_state({"psyche": 150}), room=TWO_SITES, serves=BOTH, built=150, profit=SKETCH,
                                yard=YARD)
        self.assertEqual(got.at, {"psyche": 146, "ceres": 4})
        self.assertEqual((unfx(tw.vars["sr_eb_move_from"]), unfx(tw.vars["sr_eb_move_to"])),
                         (eg.PLACES.index("psyche"), eg.PLACES.index("ceres")))
        self.assertEqual(unfx(tw.vars["sr_eb_move_carried"]), 4)

    def test_checkbox_stops_inside_the_margin(self):
        edge = eg.MARGIN * YARD
        for gap, moved in ((edge - 0.5, 0), (edge - 0.00001, 0), (edge, 4)):
            with self.subTest(gap=gap):
                got, _, _ = self.check(_state({"psyche": 150}), room=TWO_SITES, serves=BOTH, built=150,
                                       profit={"psyche": 9594, "ceres": 9594 + gap}, yard=YARD)
                self.assertEqual(got.at.get("ceres", 0), moved)

    def test_never_to_a_losing_site(self):
        """Review focus 4: every site loses money: nothing moves, and new levels go by
        grade (16 Psyche), not to the site that loses least."""
        got, _, tw = self.check(_state({"ceres": 150}), room=TWO_SITES, serves=BOTH, built=160,
                                profit={"psyche": -500, "ceres": -100}, yard=YARD)
        self.assertEqual(got.at, {"ceres": 150, "psyche": 10})
        self.assertNotIn("sr_eb_move_from", tw.vars)

    def test_new_levels_go_to_the_best_site_that_makes_money(self):
        got, _, _ = self.check(_state({"psyche": 150}), room=TWO_SITES, serves=BOTH, built=160, profit=SKETCH,
                               yard=YARD)
        self.assertEqual(got.at, {"psyche": 146, "ceres": 14})

    def test_by_hand(self):
        cases = (
            (_state({"psyche": 150}, manual=True, target={"psyche": 50, "ceres": 100}), 150, {"psyche": 146, "ceres": 4}),
            (_state({"ceres": 150}, manual=True, target={"psyche": 150}), 150, {"ceres": 146, "psyche": 4}),
            (_state({"psyche": 150}, manual=True, target={"psyche": 100}), 150, {"psyche": 150}),
            (_state({"psyche": 100}, manual=True, target={"psyche": 100, "ceres": 30}), 150, {"psyche": 120, "ceres": 30}),
        )
        for state, built, at in cases:
            with self.subTest(state=state):
                got, _, _ = self.check(state, room=TWO_SITES, serves=BOTH, built=built, profit=SKETCH, yard=YARD)
                self.assertEqual(got.at, at)
                self.assertEqual(got.target, state.target)

    def _run(self, state, months, **kw):
        """Month after month from the twin's own variables; each month's record against
        the model's."""
        vars_ = None
        for n, inputs in enumerate(months):
            merged = {**kw, **inputs}
            tw = _month_twin(state, vars_=vars_, month_index=24000 + n, **merged)
            tw.effect("sr_eb_month")
            state = _model(state, tw)
            self.assertEqual(_state_of(tw), eg.BaseState(at=state.at, target=state.target, away=state.away,
                                                         over=state.over, manual=state.manual, placed=state.placed),
                             f"month {n}")
            vars_ = tw.vars
        return state, tw

    def test_a_second_run_in_a_month_moves_nothing(self):
        """The refresh also runs the day after a base level is built (space_race_events.110):
        that run places the new levels and follows any blockade, but the month's pace and
        the move record belong to the month's first run (§ 8.5, a pace a month)."""
        kw = dict(room=TWO_SITES, serves=BOTH, profit=SKETCH, yard=YARD)
        first = _month_twin(_state({"psyche": 150}), built=150, month_index=24000, **kw)
        first.effect("sr_eb_month")
        self.assertEqual(_state_of(first).at, {"psyche": 146, "ceres": 4})
        again = _month_twin(None, vars_=first.vars, built=160, month_index=24000, **kw)
        again.effect("sr_eb_month")
        steps_2_to_4 = eg.month(dataclasses.replace(_state_of(first), placed=False), **again.model_inputs)
        self.assertEqual(_state_of(again), dataclasses.replace(steps_2_to_4, moves=()))
        self.assertEqual(_state_of(again).at, {"psyche": 146, "ceres": 14})
        self.assertEqual(unfx(again.vars["sr_eb_move_carried"]), 4)
        later = _month_twin(None, vars_=again.vars, built=160, month_index=24001, **kw)
        later.effect("sr_eb_month")
        self.assertEqual(_state_of(later).at, {"psyche": 142, "ceres": 18})
        self.assertEqual((unfx(later.vars["sr_eb_move_carried"]), unfx(later.vars["sr_eb_move_began"])), (8, 24000))

    def test_the_last_move_ends_on_the_last_month_it_carried(self):
        """§ 9.4's "Last move: 16 Psyche to Ceres, March 2071 to May 2074": the move's first
        and last months that carried levels, even when the month that finds it over comes
        after a pause (the rule switched off: no month runs)."""
        kw = dict(room=TWO_SITES, serves=BOTH, yard=YARD)
        tw = _month_twin(_state({"psyche": 150}), built=150, month_index=24000, profit=SKETCH, **kw)
        tw.effect("sr_eb_month")
        tw = _month_twin(None, vars_=tw.vars, built=150, month_index=24001, profit=SKETCH, **kw)
        tw.effect("sr_eb_month")
        self.assertEqual(unfx(tw.vars["sr_eb_move_carried"]), 8)
        level = {"psyche": 9594, "ceres": 9594}
        tw = _month_twin(None, vars_=tw.vars, built=150, month_index=24009, profit=level, **kw)
        tw.effect("sr_eb_month")
        self.assertNotIn("sr_eb_move_from", tw.vars)
        self.assertNotIn("sr_eb_move_latest", tw.vars)
        got = [unfx(tw.vars[f"sr_eb_last_{x}"]) for x in ("from", "to", "began", "ended")]
        self.assertEqual(got, [eg.PLACES.index("psyche"), eg.PLACES.index("ceres"), 24000, 24001])

    def test_the_first_placement_waits_a_month_to_move(self):
        """A first placement made mid-month (the day after the first base is built) leaves
        the moves to the next month, as the model's `placed` before this month."""
        kw = dict(room=TWO_SITES, serves=BOTH, profit=SKETCH, yard=YARD)
        first = _month_twin(eg.BaseState(), built=150, month_index=24000, **kw)
        first.effect("sr_eb_month")
        self.assertEqual(_state_of(first).at, {"ceres": 150})
        flipped = {"psyche": 11835, "ceres": 9594}
        same = _month_twin(None, vars_=first.vars, built=150, month_index=24000, **{**kw, "profit": flipped})
        same.effect("sr_eb_month")
        self.assertEqual(_state_of(same).at, {"ceres": 150})
        nxt = _month_twin(None, vars_=same.vars, built=150, month_index=24001, **{**kw, "profit": flipped})
        nxt.effect("sr_eb_month")
        self.assertEqual(_state_of(nxt).at, {"ceres": 146, "psyche": 4})

    def test_blockade_and_return_are_at_once(self):
        """Review focus 2: the levels leave at once into away, the target kept, no pace
        spent; they come back at once when the site serves again."""
        held = {"psyche": True, "ceres": True}
        for manual in (False, True):
            with self.subTest(manual=manual):
                target = {"psyche": 150} if manual else {}
                months = [dict(serves={"psyche": False, "ceres": True}, held=held), dict(serves=BOTH, held=held)]
                state, tw = self._run(_state({"psyche": 150}, manual=manual, target=target), months,
                                      room=TWO_SITES, built=150, profit=eg.profits(ASTEROID, {}), yard=YARD)
                self.assertEqual((state.at, state.away, state.target), ({"psyche": 150}, {}, target))
                self.assertNotIn("sr_eb_move_from", tw.vars)

    def test_blockade_with_room_short_goes_past_the_room_then_returns_from_there(self):
        room = {"psyche": 300, "ceres": 100}
        held = {"psyche": True, "ceres": True}
        months = [dict(serves={"psyche": False, "ceres": True}, held=held), dict(serves=held, held=held)]
        state, _ = self._run(_state({"psyche": 150}), months, room=room, built=150,
                             profit=eg.profits(ASTEROID, {}), yard=YARD)
        self.assertEqual((state.at, state.away, state.over), ({"psyche": 150}, {}, 0))

    def test_a_return_never_takes_from_a_site_that_returned(self):
        """Step 3's exclusion: a site coming back with too few levels in the pool takes the
        rest along the take order, never from itself (here the worst earner, so first in
        the checkbox's take order) or from a site that came back before it this month."""
        held = {"psyche": True, "ceres": True}
        room = {"psyche": 140, "ceres": 50}
        months = [dict(serves={"psyche": True, "ceres": False}, held=held), dict(serves=held, held=held)]
        state, _ = self._run(_state({"psyche": 100, "ceres": 50}), months, room=room, built=150,
                             profit={"psyche": 12000, "ceres": 9000}, yard=YARD)
        # Ceres takes its 50 back (10 from the pool, 40 from Psyche); then the month's move.
        self.assertEqual(state.at, {"psyche": 100 + eg.pace(150), "ceres": 50 - eg.pace(150)})
        held3 = {"psyche": True, "ceres": True, "vesta": True}
        room3 = {"psyche": 100, "ceres": 100, "vesta": 60}
        for manual in (False, True):
            with self.subTest(manual=manual):
                target = {"psyche": 100, "ceres": 100} if manual else {}
                months = [dict(serves={"psyche": False, "ceres": False, "vesta": True}, held=held3),
                          dict(serves=held3, held=held3)]
                start = _state({"psyche": 100, "ceres": 100}, manual=manual, target=target)
                state, _ = self._run(start, months, room=room3, built=200,
                                     profit={"psyche": 5000, "ceres": 4000, "vesta": 3000}, yard=YARD)
                self.assertEqual(sum(state.at.values()) + state.over, 200)

    def test_a_captured_or_ceded_site_loses_its_record(self):
        state = _state({"psyche": 100, "ceres": 50}, manual=True, target={"psyche": 100, "ceres": 50}, away={"psyche": 5})
        got, _, _ = self.check(state, room=TWO_SITES, serves={"ceres": True}, built=150, profit=SKETCH, yard=YARD)
        self.assertEqual((got.at, got.target, got.away), ({"ceres": 150}, {"ceres": 50}, {}))

    def test_room_that_shrinks_while_serving_owes_nothing_back(self):
        got, _, _ = self.check(_state({"psyche": 300}), room={"psyche": 250, "ceres": 200}, serves=BOTH, built=300,
                               profit=eg.profits(ASTEROID, {}), yard=YARD)
        self.assertEqual((got.at, got.away), ({"psyche": 250, "ceres": 50}, {}))

    def test_overflow_moves_into_new_room_at_once(self):
        profit = eg.profits(ASTEROID, {})
        months = [dict(room={"psyche": 250}, serves={"psyche": True}),
                  dict(room={"psyche": 250, "ceres": 200}, serves=BOTH)]
        state, _ = self._run(eg.BaseState(), months, built=400, profit=profit, yard=YARD)
        self.assertEqual((state.at, state.over), ({"psyche": 250, "ceres": 150}, 0))

    def test_more_levels_than_room(self):
        """Review focus 1: every place full: nothing moves."""
        got, _, tw = self.check(_state({"psyche": 300, "ceres": 200}, over=100), room=TWO_SITES, serves=BOTH,
                                built=600, profit=SKETCH, yard=YARD)
        self.assertEqual((got.at, got.over), ({"psyche": 300, "ceres": 200}, 100))
        self.assertNotIn("sr_eb_move_from", tw.vars)

    def test_lost_levels(self):
        got, _, _ = self.check(_state({"psyche": 250}, over=150), room={"psyche": 250}, serves={"psyche": True},
                               built=350, profit=eg.profits(ASTEROID, {}), yard=YARD)
        self.assertEqual((got.at, got.over), ({"psyche": 250}, 100))
        got, _, _ = self.check(_state({"psyche": 100, "ceres": 50}), room=TWO_SITES, serves=BOTH, built=130,
                               profit=SKETCH, yard=YARD)
        self.assertEqual(got.at["psyche"], 100 - 20 - eg.pace(130))

    def test_ties_go_by_place_order(self):
        """Three Rocky +10% sites earn the same: new levels fill the lowest index first, a
        move takes from the highest index first."""
        room = {"valles_marineris": 20, "olympus_mons": 20, "hellas_planitia": 20, "ceres": 300}
        serves = {p: True for p in room}
        profit = {p: 1000 for p in ("valles_marineris", "olympus_mons", "hellas_planitia")} | {"ceres": 5000}
        got, _, _ = self.check(eg.BaseState(), room=room, serves=serves, built=50, profit=profit | {"ceres": 0},
                               yard=YARD)
        self.assertEqual(got.at, {"valles_marineris": 20, "olympus_mons": 20, "hellas_planitia": 10})
        got, _, _ = self.check(got, room=room, serves=serves, built=50, profit=profit, yard=YARD)
        # The pace for 50 levels is 2, from the highest index among the tied.
        self.assertEqual(got.at, {"valles_marineris": 20, "olympus_mons": 20, "hellas_planitia": 8, "ceres": 2})

    def test_a_glut_stops_inside_the_margin_with_no_back_and_forth(self):
        """§ 10 stage 3, in script: 150 levels at 16 Psyche when Glass and Plastics go 50%
        dear; the moves stop inside the margin, all one way, and the move record follows
        (one move, Psyche to Ceres, its levels carried; then the last move)."""
        yard = eg.yardstick(ASTEROID)

        def glass(s):
            return sum(n * 70 * (1 + eg.score(p, "glass")) for p, n in s.at.items())

        for lag in (1.0, 0.25):
            with self.subTest(lag=lag):
                state, vars_, premium = _state({"psyche": 150}), None, 0.5
                start = glass(state)
                run, began, latest, ran = 0, None, None, []
                for m in range(72):
                    premium += lag * (0.5 - 0.6 * (glass(state) - start) / 26000 - premium)
                    tw = _month_twin(state, vars_=vars_, month_index=24000 + m, room=TWO_SITES, serves=BOTH,
                                     built=150, profit=eg.profits(ASTEROID, {"glass": premium}), yard=yard)
                    tw.effect("sr_eb_month")
                    nxt = _model(state, tw)
                    self.assertEqual(_state_of(tw).at, nxt.at, f"month {m}")
                    self.assertTrue(all(pair[:2] == ("psyche", "ceres") for pair in nxt.moves))
                    if nxt.moves:
                        began = 24000 + m if not run else began
                        latest = 24000 + m
                        run += sum(n for _, _, n in nxt.moves)
                        self.assertEqual(unfx(tw.vars["sr_eb_move_carried"]), run)
                        self.assertEqual(unfx(tw.vars["sr_eb_move_began"]), began)
                        self.assertEqual(unfx(tw.vars["sr_eb_move_latest"]), latest)
                    elif run:
                        # "Last move: ..., March 2071 to May 2074": its first and last months.
                        ran.append((began, latest))
                        run = 0
                    state, vars_ = nxt, tw.vars
                self.assertTrue(ran)
                self.assertNotIn("sr_eb_move_from", tw.vars)
                self.assertEqual((unfx(tw.vars["sr_eb_last_from"]), unfx(tw.vars["sr_eb_last_to"])),
                                 (eg.PLACES.index("psyche"), eg.PLACES.index("ceres")))
                self.assertEqual((unfx(tw.vars["sr_eb_last_began"]), unfx(tw.vars["sr_eb_last_ended"])), ran[-1])

    def test_random_months_match_the_model(self):
        """Random rooms, blockades, captures, losses, gains, prices, ties and toggles
        (eg.set_checkbox, eg.assign between months, as the buttons will): month after
        month the twin's record is the model's, and no loop reaches its ceiling."""
        rng = random.Random(1397)
        places = eg.PLACES
        for game in range(30):
            state = eg.BaseState()
            room = {p: rng.choice((0, 0, 50, 100, 200)) for p in places}
            for month_ in range(18):
                built = max(0, state.levels + rng.randint(-40, 60))
                held = {p: rng.random() < 0.9 for p in places}
                serves = {p: held[p] and rng.random() < 0.9 for p in places}
                if rng.random() < 0.2:
                    room = {p: max(0, r + rng.choice((-50, 0, 50))) for p, r in room.items()}
                prices = {g: rng.uniform(-0.6, 0.8) for g in eg.method_goods()}
                profit = {p: round(v) for p, v in eg.profits(ASTEROID, prices).items()}
                if rng.random() < 0.15:
                    state = eg.set_checkbox(state, on=state.manual)
                if state.manual and rng.random() < 0.3:
                    state = eg.assign(state, rng.choice(places), rng.choice((-25, -5, 5, 25)), room=room,
                                      built=built, queued=rng.randint(0, 20))
                with self.subTest(game=game, month=month_):
                    got, want, tw = self.check(state, room=room, serves=serves, held=held, built=built, profit=profit,
                                               yard=YARD)
                state = want

    def test_next_place(self):
        """§ 9.3: where the next level goes, by the rule in force, queued levels counted;
        and its grade, which the Base Room cell reads until Task 9."""
        rng = random.Random(93)
        cases = [(_state({"psyche": 290}), TWO_SITES, BOTH, 290, 5, eg.profits(ASTEROID, {})),
                 (_state({"psyche": 290}), TWO_SITES, BOTH, 290, 10, eg.profits(ASTEROID, {})),
                 (_state({"psyche": 290}), TWO_SITES, BOTH, 290, 210, eg.profits(ASTEROID, {})),
                 (_state({"psyche": 150}), TWO_SITES, BOTH, 150, 0, SKETCH),
                 (_state({"psyche": 150}, manual=True, target={"ceres": 20}), TWO_SITES, BOTH, 150, 19, SKETCH),
                 (_state({"psyche": 150}, manual=True, target={"ceres": 20}), TWO_SITES, BOTH, 150, 21, SKETCH)]
        for _ in range(40):
            room = {p: rng.choice((0, 50, 100)) for p in rng.sample(eg.PLACES, 6)}
            serves = {p: rng.random() < 0.85 for p in room}
            built = rng.randint(0, 300)
            prices = {g: rng.uniform(-0.6, 0.8) for g in eg.method_goods()}
            cases.append((eg.BaseState(), room, serves, built, rng.randint(0, 80),
                          {p: round(v) for p, v in eg.profits(ASTEROID, prices).items()}))
        for state, room, serves, built, queued, profit in cases:
            with self.subTest(state=state, room=room, queued=queued):
                tw = _month_twin(state, room=room, serves=serves, built=built, queued=queued, profit=profit,
                                 yard=YARD)
                tw.effect("sr_eb_month")
                tw.effect("sr_eb_next_place")
                after = _model(state, tw)
                i = tw.model_inputs
                want = eg.next_place(after, room=i["room"], serves=i["serves"], queued=queued, profit=i["profit"])
                self.assertEqual(unfx(tw.vars["sr_ebase_next_place"]), -1 if want is None else eg.PLACES.index(want))
                grade = gss.OVERFLOW_GRADE if want is None else ge.grade_pct(want)
                self.assertEqual(unfx(tw.vars["sr_ebase_next_grade"]), grade)

    def test_the_forecast_writer_is_ready(self):
        """Task 7's "If prices hold" and "At our assignments" row: gen_ebase.render_forecast,
        run in the twin after the month, is ebase_ground.forecast from the month's state,
        and writes no variable."""
        extra = _top_raw("\n".join(ge.render_forecast()))
        rng = random.Random(7)
        cases = [(_state({"psyche": 130, "ceres": 20}), TWO_SITES, BOTH, 150, SKETCH),
                 (_state({"psyche": 130, "ceres": 20}), TWO_SITES, BOTH, 150, {"psyche": 9594, "ceres": 9894}),
                 (_state({"psyche": 150}, manual=True, target={"psyche": 50, "ceres": 100}), TWO_SITES, BOTH, 150, SKETCH)]
        for _ in range(30):
            room = {p: rng.choice((0, 50, 100, 200)) for p in rng.sample(eg.PLACES, 8)}
            serves = {p: rng.random() < 0.9 for p in room}
            prices = {g: rng.uniform(-0.6, 0.8) for g in eg.method_goods()}
            manual = rng.random() < 0.4
            target = {p: rng.choice((0, 25, 50)) for p in room} if manual else {}
            cases.append((eg.BaseState(manual=manual, target=target), room, serves, rng.randint(0, 600),
                          {p: round(v) for p, v in eg.profits(ASTEROID, prices).items()}))
        for state, room, serves, built, profit in cases:
            with self.subTest(state=state, room=room):
                tw = _month_twin(state, room=room, serves=serves, built=built, profit=profit, yard=YARD)
                tw.effects = {**tw.effects, **extra}
                tw.effect("sr_eb_month")
                before = dict(tw.vars)
                tw.effect("sr_eb_forecast")
                self.assertEqual(tw.vars, before)
                after = _model(state, tw)
                i = tw.model_inputs
                want = eg.forecast(after, room=i["room"], serves=i["serves"], profit=i["profit"], yard=YARD)
                got = {p: int(unfx(tw.locals[f"sr_ebf_at_{p}"])) for p in eg.PLACES if tw.locals[f"sr_ebf_at_{p}"]}
                self.assertEqual(got, want.at)
                self.assertTrue(all(n <= ge.FORECAST_PASSES for n in tw.loops[-1:]))


class MonthStructureTest(unittest.TestCase):
    """The plan's Task 6 structure tests."""

    def test_month_runs_the_steps_in_order(self):
        month = _block(EFFECTS, "sr_eb_month")
        calls = ["sr_eb_read_inputs", "sr_eb_load", "sr_eb_displace", "sr_eb_return", "sr_eb_gain_lose",
                 "sr_eb_moves", "sr_eb_record_move", "sr_eb_store"]
        where = [month.index(f"{c} = yes") for c in calls]
        self.assertEqual(where, sorted(where))
        refresh = _block(MODULES, "sr_ebase_refresh")
        order = [refresh.index(f"{c} = yes") for c in ("sr_eb_count_methods", "sr_eb_month", "sr_eb_compute_mix",
                                                         "sr_eb_apply_mix", "sr_eb_next_place")]
        self.assertEqual(order, sorted(order))

    def test_every_loop_has_a_counted_ceiling(self):
        """A `while` with a `limit` runs to the engine's 1,000 passes if its exit runs away
        and logs nothing: each one's limit reads a pass counter its body increments."""
        text = EFFECTS
        loops = [m.start() for m in re.finditer(r"while = \{", text)]
        self.assertGreater(len(loops), 0)
        for at_ in loops:
            body = _block(text[at_:], "while")
            limit = _block(body, "limit")
            counter = re.search(r"local_var:(\w+_(?:pass|tpass|gpass)) < (\d+)", limit)
            self.assertIsNotNone(counter, limit)
            self.assertIn(f"change_local_variable = {{ name = {counter.group(1)} add = 1 }}", body)
            self.assertLessEqual(int(counter.group(2)), len(eg.PLACES) + 1)
            self.assertNotIn("count =", body)

    def test_move_loop_is_bounded_by_the_pace(self):
        moves = _block(EFFECTS, "sr_eb_moves")
        self.assertIn("set_local_variable = { name = sr_ebm_left value = local_var:sr_ebi_pace }", moves)
        limit = _block(_block(moves, "while"), "limit")
        self.assertIn("local_var:sr_ebm_left > 0", limit)
        self.assertIn(f"local_var:sr_ebm_pass < {ge.MONTH_PASSES}", limit)
        self.assertEqual(ge.MONTH_PASSES, 42)
        move = _block(EFFECTS, "sr_eb_move_pass")
        self.assertIn("set_local_variable = { name = sr_ebm_n value = { value = local_var:sr_ebm_srcn "
                      "max = local_var:sr_ebm_dstn max = local_var:sr_ebm_left } }", move)
        self.assertIn("change_local_variable = { name = sr_ebm_left subtract = local_var:sr_ebm_n }", move)
        inputs = _block(EFFECTS, "sr_eb_read_places")
        self.assertIn(f"value = {{ value = local_var:sr_ebi_built divide = {eg.PACE_MONTHS} ceiling = yes min = 1 }}",
                      inputs)
        self.assertIn("set_local_variable = { name = sr_ebi_built value = sr_ebase_levels }", inputs)

    def test_checkbox_margin_reads_the_yardstick(self):
        move = _block(EFFECTS, "sr_eb_move_pass")
        self.assertIn("local_var:sr_ebm_dstp > 0 local_var:sr_ebm_gap > 0 local_var:sr_ebm_gap >= local_var:sr_ebi_margin",
                      move)
        profits = _block(EFFECTS, "sr_eb_read_profits")
        self.assertIn("set_local_variable = { name = sr_ebi_yard value = sr_eb_yardstick }", profits)
        self.assertIn(f"set_local_variable = {{ name = sr_ebi_margin value = {{ value = local_var:sr_ebi_yard "
                      f"multiply = {ge.num(eg.MARGIN)} }} }}", profits)

    def test_the_profit_stub_sets_what_the_real_reader_sets(self):
        profits = _block(EFFECTS, "sr_eb_read_profits")
        sets = set(re.findall(r"set_local_variable = \{ name = (\w+)", profits))
        want = ({f"sr_ebi_p_{k}" for k in eg.PLACES} | {f"sr_ebi_m_{t}" for t in eg.TYPES}
                | {"sr_ebi_yard", "sr_ebi_margin", "sr_ebi_p_over"})
        self.assertEqual(sets, want)
        for k in eg.PLACES:
            with self.subTest(place=k):
                self.assertIn(f"set_local_variable = {{ name = sr_ebi_p_{k} value = {{ value = "
                              f"local_var:sr_ebi_m_{eg.GROUND[k]} multiply = {100 + ge.grade_pct(k)} divide = 100 }} }}",
                              profits)
        # Only the reader reads the margins' locals.
        outside = EFFECTS.replace(profits, "")
        self.assertNotIn("local_var:sr_ebi_m_", outside)

    def test_every_place_in_every_pass(self):
        for effect in ("sr_eb_displace", "sr_eb_return", "sr_eb_place_new", "sr_eb_take_return", "sr_eb_take_lost",
                       "sr_eb_move_pass", "sr_eb_load", "sr_eb_store", "sr_eb_next_give"):
            body = _block(EFFECTS, effect)
            fam = "sr_ebn" if effect == "sr_eb_next_give" else "sr_ebm"
            for k in eg.PLACES:
                with self.subTest(effect=effect, place=k):
                    self.assertRegex(body, rf"\b{fam}_at_{k}\b")
        move = _block(EFFECTS, "sr_eb_move_pass")
        manual, checkbox = move.split("else = {", 1)
        for k in eg.PLACES:
            with self.subTest(place=k):
                # By hand, both chains; with the checkbox, both searches.
                self.assertEqual(manual.count(f"local_var:sr_ebm_at_{k} > local_var:sr_ebr_tg_{k}"), 1)
                self.assertEqual(manual.count(f"local_var:sr_ebm_at_{k} < local_var:sr_ebr_tg_{k}"), 1)
                self.assertIn(f"local_var:sr_ebm_at_{k} > 0 local_var:sr_ebi_p_{k} <= local_var:sr_ebm_srcp", checkbox)
                self.assertIn(f"local_var:sr_ebi_room_{k} > local_var:sr_ebm_at_{k} local_var:sr_ebi_p_{k} > "
                              "local_var:sr_ebm_dstp", checkbox)

    def test_profit_searches_break_ties_by_place_order(self):
        """Every place, in index order: the worst earner in use keeps ties to the higher
        index (<=), the best with free room keeps them to the lower (>), in the move pass,
        the give and the take."""
        for effect, fam, worst, best in (("sr_eb_move_pass", "sr_ebm", "srcp", "dstp"),
                                         ("sr_eb_place_new", "sr_ebm", None, "gdstp"),
                                         ("sr_eb_next_give", "sr_ebn", None, "gdstp"),
                                         ("sr_eb_take_lost", "sr_ebm", "tsrcp", None),
                                         ("sr_eb_take_return", "sr_ebm", "tsrcp", None)):
            body = _block(EFFECTS, effect)
            if worst:
                found = re.findall(rf"local_var:{fam}_at_(\w+) > 0(?: local_var:sr_ebr_ret_\w+ = 0)? "
                                   rf"local_var:sr_ebi_p_(\w+) <= local_var:{fam}_{worst} \}}", body)
                with self.subTest(effect=effect, search="worst"):
                    self.assertEqual([a for a, b in found if a == b], list(eg.PLACES))
            if best:
                found = re.findall(rf"local_var:sr_ebi_room_(\w+) > local_var:{fam}_at_(\w+) "
                                   rf"local_var:sr_ebi_p_(\w+) > local_var:{fam}_{best} \}}", body)
                with self.subTest(effect=effect, search="best"):
                    self.assertEqual([a for a, b, c in found if a == b == c], list(eg.PLACES))
        take = _block(EFFECTS, "sr_eb_take_return")
        for k in eg.PLACES:
            with self.subTest(place=k):
                self.assertEqual(take.count(f"local_var:sr_ebr_ret_{k} = 0"), 3)
        self.assertNotIn("sr_ebr_ret_", _block(EFFECTS, "sr_eb_take_lost"))

    def test_orders_are_the_model_s(self):
        """By grade, best first, ties by place order (ebase_ground.by_grade, which is
        gen_solar_sites.ebase_tiers); taking, the reverse."""
        tiers = [eg.NEAR_EARTH if t is None else t.key for t in gss.ebase_tiers()]
        self.assertEqual(eg.by_grade(), tiers)
        give = _block(EFFECTS, "sr_eb_place_new")
        grade_pass = give[give.rindex("while = {"):]
        found = re.findall(r"limit = \{ local_var:sr_ebm_pool > 0 local_var:sr_ebi_room_(\w+) > ", grade_pass)
        self.assertEqual(found, eg.by_grade())
        take = _block(EFFECTS, "sr_eb_take_lost")
        found = re.findall(r"local_var:sr_ebm_need > 0 local_var:sr_ebm_at_(\w+) > 0 \}", take)
        self.assertEqual(found, list(reversed(eg.by_grade())))

    def test_first_placement_is_unpaced(self):
        month = _block(EFFECTS, "sr_eb_month")
        paced = _block(month[month.index("set_local_variable = { name = sr_ebm_mn value = 0 }"):], "if")
        limit = _block(paced, "limit")
        self.assertIn("has_variable = sr_eb_placed", limit)
        self.assertIn("var:sr_eb_moved_month < te_history_month_index", limit)
        self.assertIn("NOT = { has_variable = sr_eb_moved_month }", limit)
        self.assertIn("sr_eb_moves = yes", paced)
        self.assertIn("sr_eb_record_move = yes", paced)
        self.assertEqual(month.count("sr_eb_moves = yes"), 1)
        self.assertEqual(month.count("sr_eb_record_move = yes"), 1)
        self.assertLess(month.index("sr_eb_moves = yes"), month.index("set_variable = { name = sr_eb_placed value = yes }"))
        self.assertIn("local_var:sr_ebi_built > 0 NOT = { has_variable = sr_eb_placed }", month)

    def test_variables_on_the_country(self):
        """A revolution's winner keeps country variables, not modifiers or lists: no
        variable is set or read in a state or a building, and every count is stored."""
        text = EFFECTS
        for m in re.finditer(r"every_scope_(?:state|building) = \{", text):
            body = _block(text[m.start():], m.group(0)[:-4].strip())
            self.assertNotRegex(body, r"\b(set|change|remove)_variable\b")
            self.assertNotRegex(body, r"(?<!root\.)\bvar:")
        store = _block(EFFECTS, "sr_eb_store")
        for k in eg.PLACES:
            for var in (f"sr_eb_at_{k}", f"sr_eb_target_{k}", f"sr_eb_away_{k}"):
                with self.subTest(var=var):
                    self.assertIn(f"set_variable = {{ name = {var} value = ", store)
        self.assertNotIn("_list", text)

    def test_locals_have_their_own_prefixes(self):
        """Locals are shared by every effect a call runs: the generated effects use only
        their own families, and no other file uses them."""
        prefixes = ("sr_ebm_", "sr_ebf_", "sr_ebn_", "sr_ebi_", "sr_ebr_", "sr_ebc_", "sr_ebx_", "sr_ebt_", "sr_eba_",
                    "sr_ebq_")
        names = set(re.findall(r"(?:set|change)_local_variable = \{ name = (\w+)", EFFECTS))
        names |= set(re.findall(r"local_var:(\w+)", EFFECTS))
        names -= {"sr_eb_next_left", "sr_eb_next_found"}
        self.assertTrue(all(n.startswith(prefixes) for n in names), sorted(n for n in names if not n.startswith(prefixes)))
        import glob
        for path in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True):
            if os.path.samefile(path, os.path.join(REPO, ge.EFFECTS_OUT)):
                continue
            text = open(path, encoding="utf-8-sig").read()
            with self.subTest(path=os.path.relpath(path, REPO)):
                self.assertNotRegex(text, r"local_var:sr_eb[mfnircxtaq]_|name = sr_eb[mfnircxtaq]_")


class MixSelfCheckTest(unittest.TestCase):
    """TE_SELF_CHECK ebase_mix (plan Task 5 step 3): armed on a base with a mix of at
    least 1.5% of Tech-Critical Metals, the verdict a month later on a mix at least two
    days old; OK can't pass on a modifier that never arrived."""

    def _twin(self, at, mods):
        tw = _twin_base(at, built=sum(at.values()), rooms={p: 300 for p in at})
        tw.buildings = [Building(1, level=sum(at.values()), mods=mods)]
        return tw

    def _month(self, tw, index):
        tw.stub_values["te_history_month_index"] = fx(index)
        tw.vars.pop("sr_eb_mix_fresh", None)
        tw.effect("sr_ebase_refresh")

    def test_ok_after_a_month(self):
        tw = self._twin({"psyche": 100}, {})
        self._month(tw, 100)   # applies the mix; the check has nothing to read yet
        self._month(tw, 101)   # arms
        self.assertIn("sr_eb_mix_check_armed", tw.vars)
        self.assertEqual(tw.logs, [])
        self._month(tw, 102)   # the verdict
        self.assertEqual(len(tw.logs), 1)
        self.assertIn("TE_SELF_CHECK OK ebase_mix", tw.logs[0])
        self.assertAlmostEqual(unfx(tw.vars["sr_eb_mix_check_read"]),
                               eg.mix("metallic")["tech_metals"], delta=1e-4)
        self._month(tw, 103)
        self.assertEqual(len(tw.logs), 1, "once a game")

    def test_broken_when_the_modifier_never_arrives(self):
        tw = self._twin({"psyche": 100}, {})
        self._month(tw, 100)
        self._month(tw, 101)
        tw.buildings[0].mods.clear()
        tw.stub_values["te_history_month_index"] = fx(102)
        tw.vars.pop("sr_eb_mix_fresh", None)
        tw.effect("sr_eb_mix_self_check")
        self.assertIn("TE_SELF_CHECK BROKEN ebase_mix", tw.logs[0])

    def test_no_verdict_on_a_fresh_mix_or_a_small_one(self):
        tw = self._twin({"psyche": 100}, {})
        self._month(tw, 100)
        self._month(tw, 101)
        tw.stub_values["te_history_month_index"] = fx(102)
        tw.effect("sr_eb_mix_self_check")   # last refresh's marker still on: wait
        self.assertEqual(tw.logs, [])
        # A Mixed base has no Tech-Critical mix: never armed, so OK can't pass on 0.
        tw = self._twin({"near_earth": 10}, {})
        for m in range(100, 104):
            self._month(tw, m)
        self.assertNotIn("sr_eb_mix_check_armed", tw.vars)
        self.assertEqual(tw.logs, [])

    def test_a_new_building_waits_for_its_refresh(self):
        """F2 of the Tasks 5 and 6 review: a base building built in the verdict's month
        gets its refresh from space_race_events.110 the next day. Its immediate, as the
        events file has it, gives no verdict that day (the marker stands through the
        refresh), and the month's pulse then reads OK on both buildings."""
        events = _raw("events", "space_race_events.txt")
        body = _block(_strip(events), "space_race_events.110")
        immediate = _block(body, "immediate")
        tw = self._twin({"psyche": 100}, {})
        self._month(tw, 100)
        self._month(tw, 101)
        tw.stub_values["te_history_month_index"] = fx(102)
        tw.vars.pop("sr_eb_mix_fresh", None)
        tw.buildings.insert(0, Building(2, level=5))   # finished yesterday: no mix of ours yet
        tw.stub_values["sr_ebase_levels"] = fx(105)
        tw.vars["sr_ebase_hook_pending"] = SCALE
        tw.run(_parse(_tokens(immediate))[0])
        self.assertEqual(tw.logs, [])
        self.assertNotIn("sr_ebase_hook_pending", tw.vars)
        self._month(tw, 102)
        self.assertEqual(len(tw.logs), 1)
        self.assertIn("TE_SELF_CHECK OK ebase_mix", tw.logs[0])
        self.assertEqual(unfx(tw.vars["sr_eb_mix_check_match"]), 2)

    def test_every_building_is_read(self):
        """OK only if every base building matches, BROKEN if none does, and a month
        later if some do (a building no refresh has reached)."""
        tw = self._twin({"psyche": 100}, {})
        tw.buildings.append(Building(3, level=1))
        self._month(tw, 100)
        self._month(tw, 101)
        tw.buildings[1].mods.clear()              # one building lost its mix
        tw.stub_values["te_history_month_index"] = fx(102)
        tw.vars.pop("sr_eb_mix_fresh", None)
        tw.effect("sr_eb_mix_self_check")
        self.assertEqual(tw.logs, [])
        self.assertEqual(unfx(tw.vars["sr_eb_mix_check_armed"]), 102)
        self.assertNotIn("sr_eb_mix_checked", tw.globals)
        for b in tw.buildings:
            b.mods.clear()
        tw.stub_values["te_history_month_index"] = fx(103)
        tw.effect("sr_eb_mix_self_check")
        self.assertIn("TE_SELF_CHECK BROKEN ebase_mix", tw.logs[0])
        self.assertEqual(unfx(tw.vars["sr_eb_mix_check_miss"]), 2)
        self.assertEqual(unfx(tw.vars["sr_eb_mix_check_read"]), 0)

    def test_the_tolerance_catches_a_multiplier_read_as_1(self):
        """F3: a unit modifier at multiplier 1 reads 0.01 against a mix at the 1.5% floor
        (0.015, gap 0.005): BROKEN, where the old 0.005 tolerance let it pass."""
        body = _block(_strip(_raw("common", "scripted_effects", "sr_colony_module_effects.txt")), "sr_eb_mix_self_check")
        self.assertIn("local_var:sr_ebk_gap <= 0.001", body)
        self.assertIn("local_var:sr_ebk_gap >= -0.001", body)
        self.assertNotIn("0.005", body)
        self.assertNotIn("random_scope_building", body)

    def test_the_self_check_row(self):
        playtest = _raw("docs", "testing", "solar-colonies-playtest.md")
        self.assertIn("`TE_SELF_CHECK OK/BROKEN ebase_mix", playtest)



# ---------------------------------------------------------------------------
# Task 7: the checkbox, the buttons, the forecast, the totals and the notice
# ---------------------------------------------------------------------------

SGUIS = _strip(_raw("common", "scripted_guis", "sr_colony_sguis.txt"))
AUTO, ASSIGN_SGUI = "sr_ebase_auto_sgui", "sr_ebase_assign_sgui"
OPS = {1: 5, 2: -5, 3: 25, 4: -25}  # scope:op: the step it makes
_SCRIPTED = {**_top_raw(_raw(str(ge.EFFECTS_OUT))),
             **_top_raw(_raw("common", "scripted_effects", "sr_colony_module_effects.txt"))}


def _calls(body):
    """The scripted effects a body calls, and those they call, all the way down."""
    seen, todo = set(), [body]
    while todo:
        for name_ in re.findall(r"\b(\w+) = yes\b", _strip(todo.pop())):
            if name_ in _SCRIPTED and name_ not in seen:
                seen.add(name_)
                todo.append(_SCRIPTED[name_])
    return seen


def _callers(effect):
    """Every block in common/ that calls `effect`: scripted effects by name, and each
    scripted GUI."""
    out = {n for n, b in _SCRIPTED.items() if re.search(rf"\b{effect} = yes", _strip(b))}
    out |= {n for n, b in _top_raw(_raw("common", "scripted_guis", "sr_colony_sguis.txt")).items()
            if re.search(rf"\b{effect} = yes", _strip(b))}
    return out


def _market_twin(state, *, room, serves=None, built, queued=0, prices=None, methods=None, is_ai=False,
                 month_index=24000, logistics=None):
    """A month twin whose profits come from the real reader: base buildings on `methods`
    (pm -> levels, default all Asteroid Mines), each on the logistics methods `logistics`
    gives it (pm -> methods, default none), and these market premiums."""
    serves = {p: True for p in room} if serves is None else serves
    tw = _month_twin(state, room=room, serves=serves, built=built, queued=queued, profit={}, yard=YARD,
                     month_index=month_index)
    del tw.stub_effects["sr_eb_read_profits"]
    tw.is_ai = is_ai
    methods = methods or {"pm_space_mine": max(built, 1)}
    logistics = logistics or {}
    for n, (pm, levels) in enumerate(methods.items()):
        tw.buildings.append(Building(n, level=levels, pm=pm, logistics=logistics.get(pm, ())))
    for g, r in (prices or {}).items():
        tw.price(g, r)
    tw.effect("sr_eb_count_methods")
    total = sum(methods.values())
    tw.shares = {pm: n / total for pm, n in methods.items()}
    tw.cuts = eg.method_cuts([(pm, n, logistics.get(pm, ())) for pm, n in methods.items()])
    tw.rel = {g: round(r, 5) for g, r in (prices or {}).items()}
    return tw


def _model_room(tw):
    """The room the buttons cap at, place by place: a place's room while we hold it."""
    i = tw.model_inputs
    return {p: i["room"].get(p, 0) if i["held"].get(p) else 0 for p in eg.PLACES}


class ControlsStructureTest(unittest.TestCase):
    """The plan's Task 7 structure tests."""

    def test_buttons_never_move_levels(self):
        """Neither scripted GUI's effect, nor anything it calls, writes where the levels
        work, so a click moves no level and switching the checkbox twice gains nothing
        (review focus 5: only the month moves, once a month, at its pace)."""
        for sgui in (AUTO, ASSIGN_SGUI):
            effect = _block(_block(SGUIS, sgui), "effect")
            called = _calls(effect)
            with self.subTest(sgui=sgui):
                self.assertIn("sr_eb_after_click", called)
                self.assertTrue(called.isdisjoint({"sr_eb_month", "sr_eb_moves", "sr_eb_store", "sr_eb_place_new",
                                                   "sr_eb_gain_lose"}), called)
                for body in [effect] + [_SCRIPTED[c] for c in called]:
                    self.assertNotRegex(_strip(body), r"(?:set|change|remove)_variable = (?:\{ name = )?sr_eb_(?:at_|over\b)")

    def test_the_work_waits_for_the_click(self):
        """A tooltip walks a scripted GUI's effect every frame of a hover: every call in
        each effect sits behind the click-only marker, set just before and removed
        first inside (scripting_best_practices.md, "An Option's Tooltip Walks Its
        Effects")."""
        for sgui in (AUTO, ASSIGN_SGUI):
            effect = _block(_block(SGUIS, sgui), "effect")
            with self.subTest(sgui=sgui):
                at_ = effect.index("set_variable = sr_eb_click")
                guarded = _block(effect[at_:], "if")
                self.assertTrue(guarded.strip().startswith("limit = { has_variable = sr_eb_click }"))
                self.assertIn("remove_variable = sr_eb_click", guarded.split("\n")[1] + guarded.split("\n")[2])
                outside = effect.replace(guarded, "")
                self.assertEqual(re.findall(r"\b(\w+) = yes", outside), [])

    def test_plus_needs_an_unassigned_level(self):
        """is_valid: plus (ops 1 and 3) needs the targets' sum below built plus queued
        levels and the place below its room; minus (2 and 4) a target above 0. Each
        condition is a custom_tooltip, so the button carries its reasons."""
        valid = _block(_block(SGUIS, ASSIGN_SGUI), "is_valid")
        minus = _block(valid, "trigger_if")
        self.assertIn("scope:op = 2", minus)
        self.assertIn("scope:op = 4", minus)
        self.assertRegex(minus, r"custom_tooltip = \{\s*text = sr_ebase_assign_req_assigned_tt\s*sr_eb_scope_target > 0\s*\}")
        plus = _block(valid, "trigger_else")
        self.assertRegex(plus, r"custom_tooltip = \{\s*text = sr_ebase_assign_req_unassigned_tt\s*"
                               r"sr_eb_assigned < sr_ebase_queued_levels\s*\}")
        self.assertRegex(plus, r"custom_tooltip = \{\s*text = sr_ebase_assign_req_room_tt\s*"
                               r"sr_eb_scope_target < sr_eb_scope_room\s*\}")

    def test_notice_threshold_and_throttle(self):
        notice = _block(EFFECTS, "sr_eb_move_notice")
        limit = _block(notice, "limit")
        for line in ("is_ai = no", "NOT = { has_variable = sr_eb_manual }", "has_variable = sr_eb_move_carried",
                     "var:sr_eb_move_carried >= sr_eb_notice_threshold",
                     "NOT = { has_variable = sr_eb_notice_next }", "te_history_month_index >= var:sr_eb_notice_next"):
            with self.subTest(line=line):
                self.assertIn(line, limit)
        self.assertEqual(_block(VALUES, "sr_eb_notice_threshold").strip(),
                         f"value = sr_ebase_levels multiply = {ge.num(eg.NOTICE_SHARE)}")
        self.assertIn("local_var:sr_ebq_same = 0 NOT = { local_var:sr_ebq_ft = local_var:sr_ebq_tt }", notice)
        self.assertIn(f"value = {{ value = te_history_month_index add = {eg.NOTICE_GAP_MONTHS} }}", notice)
        self.assertEqual(eg.NOTICE_GAP_MONTHS, 12)
        self.assertEqual(notice.count("post_notification = sr_ebase_move_notice"), 1)
        messages = _strip(_raw("common", "messages", "extra_messages.txt"))
        body = _block(messages, "sr_ebase_move_notice")
        self.assertIn("type = country", body)
        self.assertIn("notification_type = feed", body)

    def test_totals_skip_the_ai(self):
        refresh = _block(MODULES, "sr_ebase_refresh")
        players = refresh[refresh.index("limit = { is_ai = no }"):]
        players = players[:players.index("}", players.index("sr_eb_move_notice = yes"))]
        for call in ("sr_eb_forecast", "sr_eb_totals", "sr_eb_move_notice"):
            with self.subTest(call=call):
                self.assertIn(f"{call} = yes", players)
                self.assertEqual(refresh.count(f"{call} = yes"), 1)
        self.assertLess(refresh.index("sr_eb_month = yes"), refresh.index("sr_eb_totals = yes"))
        self.assertEqual(_callers("sr_eb_totals"), {"sr_ebase_refresh", "sr_eb_after_click"})
        self.assertEqual(_callers("sr_eb_after_click"), {AUTO, ASSIGN_SGUI})

    def test_only_the_checkbox_sets_manual(self):
        """sr_eb_manual is set only by sr_eb_checkbox_off, which only the two scripted
        GUIs reach, and both are shown only to players (the AI always runs the
        checkbox)."""
        import glob
        setters = []
        for path in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True):
            text = _strip(open(path, encoding="utf-8-sig").read())
            for name_, body in _top_raw(text).items():
                if re.search(r"set_variable = (?:\{ name = )?sr_eb_manual\b", body):
                    setters.append(name_)
        self.assertEqual(setters, ["sr_eb_checkbox_off"])
        self.assertEqual(_callers("sr_eb_checkbox_off"), {AUTO, "sr_eb_assign"})
        self.assertEqual(_callers("sr_eb_assign"), {ASSIGN_SGUI})
        for sgui in (AUTO, ASSIGN_SGUI):
            with self.subTest(sgui=sgui):
                self.assertEqual(_block(_block(SGUIS, sgui), "is_shown").strip(), "is_ai = no")
                self.assertEqual(_block(_block(SGUIS, sgui), "ai_is_valid").strip(), "always = no")
        self.assertIn("saved_scopes = { site op }", _block(SGUIS, ASSIGN_SGUI))
        self.assertNotIn("saved_scopes", _block(SGUIS, AUTO))


class ControlsTwinTest(unittest.TestCase):
    """The scripted GUIs, the totals and the notice run in the twin against the model:
    eg.set_checkbox, eg.assign, eg.totals and eg.forecast, eg.notice_due and
    eg.notice_good."""

    def _random_state(self, rng):
        room = {p: rng.choice((0, 50, 100, 200)) for p in rng.sample(eg.PLACES, 8)}
        held = {p: rng.random() < 0.9 for p in room}
        serves = {p: held[p] and rng.random() < 0.85 for p in room}
        built = rng.randint(0, 500)
        manual = rng.random() < 0.5
        state = eg.BaseState(manual=manual, target={p: rng.choice((0, 5, 25, 60)) for p in room} if manual else {})
        return state, room, held, serves, built

    def _after_month(self, rng, **extra):
        """A twin after a random month (a first placement, then a month that moves)."""
        state, room, held, serves, built = self._random_state(rng)
        tw = _month_twin(state, room=room, serves=serves, held=held, built=built, queued=rng.randint(0, 30),
                         profit={p: round(v) for p, v in eg.profits(ASTEROID, {g: rng.uniform(-0.5, 0.6) for g in
                                                                             eg.method_goods()}).items()},
                         yard=YARD, **extra)
        tw.effect("sr_eb_month")
        for _ in range(rng.randint(0, 2)):
            tw.effect("sr_eb_month")
        return tw

    def test_the_checkbox_is_the_model_s(self):
        """Off: every target is the place's at + away, sr_eb_manual set; on: the targets
        dropped, sr_eb_manual cleared. No level moves either way."""
        rng = random.Random(71)
        for case in range(40):
            tw = self._after_month(rng)
            before = _state_of(tw)
            with self.subTest(case=case, manual=before.manual):
                tw.click(AUTO)
                want = eg.set_checkbox(before, on=before.manual)
                self.assertEqual(_state_of(tw), want)
                tw.click(AUTO)
                self.assertEqual(_state_of(tw), eg.set_checkbox(want, on=want.manual))
                self.assertEqual(_state_of(tw).at, before.at)
                self.assertEqual(_state_of(tw).over, before.over)
        # A blockaded 16 Psyche: its levels work at Ceres and are owed back, so switching
        # the checkbox off assigns them to both (ebase_ground.set_checkbox's at + away).
        tw = _month_twin(_state({"psyche": 150}), room=TWO_SITES, serves={"psyche": False, "ceres": True},
                         held=BOTH, built=150, profit=SKETCH, yard=YARD)
        tw.effect("sr_eb_month")
        self.assertEqual((_state_of(tw).at, _state_of(tw).away), ({"ceres": 150}, {"psyche": 150}))
        tw.click(AUTO)
        self.assertEqual(_state_of(tw).target, {"psyche": 150, "ceres": 150})

    def test_the_buttons_are_the_model_s(self):
        """Each op at each place held or not: the click sets the target eg.assign sets
        (the checkbox switched off first), and is_valid holds exactly when the model's
        click changes the target."""
        rng = random.Random(72)
        for case in range(30):
            tw = self._after_month(rng)
            room = _model_room(tw)
            built, queued = tw.model_inputs["built"], unfx(tw.stub_values["sr_ebase_queued_levels"]) - tw.model_inputs["built"]
            vars_ = dict(tw.vars)
            ours = {eg.PLACES.index(p) for p, r in tw.model_inputs["room"].items() if r}
            for site in sorted(ours | set(rng.sample(range(len(eg.PLACES)), 2))):
                place = eg.PLACES[site]
                for op, step in OPS.items():
                    with self.subTest(case=case, place=place, op=op):
                        tw.vars = dict(vars_)
                        before = _state_of(tw)
                        valid = tw.valid(ASSIGN_SGUI, site=site, op=op)
                        tw.click(ASSIGN_SGUI, site=site, op=op)
                        want = eg.assign(before, place, step, room=room, built=built, queued=int(queued))
                        self.assertEqual(_state_of(tw), want)
                        changed = want.target.get(place, 0) != eg.set_checkbox(before, on=False).target.get(place, 0)
                        self.assertEqual(valid, changed)
        # A blockaded 16 Psyche owes 150 back, which counts as assigned: with 20 queued,
        # 300 assigned against 170 built and queued, so + at Ceres can't add one.
        tw = _month_twin(_state({"psyche": 150}), room=TWO_SITES, serves={"psyche": False, "ceres": True},
                         held=BOTH, built=150, queued=20, profit=SKETCH, yard=YARD)
        tw.effect("sr_eb_month")
        ceres = eg.PLACES.index("ceres")
        self.assertFalse(tw.valid(ASSIGN_SGUI, site=ceres, op=1))
        self.assertTrue(tw.valid(ASSIGN_SGUI, site=ceres, op=2))

    def test_a_hover_writes_nothing_and_runs_no_heavy_work(self):
        """The tooltip walk of each scripted GUI: no variable changes, no read of an unset
        variable or local (the twin fails on one, as the engine logs one), and none of
        the work behind the marker runs; the lines it shows say what the click does."""
        rng = random.Random(73)
        for case in range(10):
            tw = self._after_month(rng)
            vars_ = dict(tw.vars)
            for sgui, saved in ((AUTO, {}), *((ASSIGN_SGUI, {"site": s, "op": o}) for s in (0, 8, 40) for o in OPS)):
                with self.subTest(case=case, sgui=sgui, saved=saved):
                    tw.calls, tw.tooltips, tw.locals = [], [], {}
                    tw.click(sgui, walk=True, **saved)
                    self.assertEqual(tw.vars, vars_)
                    self.assertEqual(tw.calls, [])
                    self.assertTrue(tw.tooltips)
                    if sgui == ASSIGN_SGUI:
                        manual = "sr_eb_manual" in vars_
                        self.assertEqual("sr_ebase_assign_switch_off_tt" in tw.tooltips, not manual)
                        sign = "plus" if OPS[saved["op"]] > 0 else "minus"
                        self.assertIn(f"sr_ebase_assign_{sign}_{abs(OPS[saved['op']])}_tt", tw.tooltips)
                    else:
                        self.assertEqual(tw.tooltips, ["sr_ebase_auto_on_tt" if "sr_eb_manual" in vars_
                                                       else "sr_ebase_auto_off_tt"])

    def test_switching_twice_in_a_month_moves_no_more_than_the_pace(self):
        """Review focus 5: off and on again within a month; the month's second run (a
        build day) moves nothing more; the next month moves the pace."""
        kw = dict(room=TWO_SITES, serves=BOTH, profit=SKETCH, yard=YARD)
        tw = _month_twin(_state({"psyche": 150}), built=150, month_index=24000, **kw)
        tw.effect("sr_eb_month")
        self.assertEqual(_state_of(tw).at, {"psyche": 146, "ceres": 4})
        tw.click(AUTO)
        tw.click(AUTO)
        again = _month_twin(None, vars_=tw.vars, built=150, month_index=24000, **kw)
        again.effect("sr_eb_month")
        self.assertEqual(_state_of(again).at, {"psyche": 146, "ceres": 4})
        nxt = _month_twin(None, vars_=again.vars, built=150, month_index=24001, **kw)
        nxt.effect("sr_eb_month")
        self.assertEqual(_state_of(nxt).at, {"psyche": 142, "ceres": 8})

    def test_totals_match_the_model(self):
        """"Now" is eg.totals of the record; the second row eg.totals of eg.forecast,
        from the refresh's path (after the month) and from a click's
        (sr_eb_after_click), at market prices and on mixed methods."""
        rng = random.Random(74)
        pms = list(eg.mining_methods())
        for case in range(16):
            state, room, held, serves, built = self._random_state(rng)
            prices = {g: rng.uniform(-0.6, 0.9) for g in eg.method_goods()}
            methods = {pm: rng.choice((0, 5, 40)) for pm in pms} | {pms[0]: rng.randint(1, 60)}
            methods = {pm: n for pm, n in methods.items() if n}
            tw = _market_twin(state, room={p: r for p, r in room.items() if held[p]},
                              serves={p: serves[p] for p in room if held[p]}, built=built, prices=prices,
                              methods=methods,
                              logistics={pm: tuple(c for c in eg.input_cuts() if rng.random() < 0.5) for pm in methods})
            tw.effect("sr_eb_month")
            for path in ("refresh", "click"):
                with self.subTest(case=case, path=path):
                    if path == "refresh":
                        tw.effect("sr_eb_forecast")
                        tw.effect("sr_eb_totals")
                    else:
                        tw.locals = {}
                        tw.effect("sr_eb_after_click")
                    now = _state_of(tw)
                    i = tw.model_inputs
                    profit = {k: unfx(tw.locals[f"sr_ebi_p_{k}"]) for k in eg.PLACES}
                    end = eg.forecast(now, room=i["room"], serves=i["serves"], profit=profit,
                                      yard=unfx(tw.locals["sr_ebi_yard"]))
                    got_end = {p: int(unfx(tw.locals[f"sr_ebf_at_{p}"])) for p in eg.PLACES
                               if tw.locals[f"sr_ebf_at_{p}"]}
                    self.assertEqual(got_end, end.at)
                    for row, st in (("now", now), ("end", end)):
                        want = eg.totals(st, tw.shares, tw.rel, tw.cuts)
                        for g in (*eg.GOODS, "profit"):
                            got = unfx(tw.vars[f"sr_eb_{row}_{g}"])
                            self.assertAlmostEqual(got, want[g], delta=0.5 + 2e-6 * abs(want[g]), msg=f"{row} {g}")

    def test_the_month_s_figures_are_stored(self):
        """The contract's stored readings (F4 of the Tasks 5 and 6 review): each place's
        profit a level, the yardstick and the lead method, at every refresh for every
        country; a click reads them back and evaluates no margin."""
        rng = random.Random(76)
        pms = list(eg.mining_methods())
        for case in range(8):
            state, room, held, serves, built = self._random_state(rng)
            methods = {pm: n for pm, n in zip(pms, [rng.choice((0, 3, 20)) for _ in pms]) if n} or {pms[1]: 4}
            tw = _market_twin(state, room={p: r for p, r in room.items() if held[p]}, built=built,
                              prices={g: rng.uniform(-0.5, 0.8) for g in eg.method_goods()}, methods=methods,
                              is_ai=rng.random() < 0.5,
                              logistics={pm: tuple(c for c in eg.input_cuts() if rng.random() < 0.5) for pm in methods})
            tw.effect("sr_eb_month")
            with self.subTest(case=case):
                for k in eg.PLACES:
                    self.assertAlmostEqual(unfx(tw.vars[f"sr_eb_level_profit_{k}"]),
                                           eg.profit_a_level(k, tw.shares, tw.rel, tw.cuts), delta=0.05)
                self.assertAlmostEqual(unfx(tw.vars["sr_eb_yardstick"]), eg.yardstick(tw.shares, tw.cuts), delta=0.05)
                self.assertEqual(unfx(tw.vars["sr_eb_lead_method"]), eg.lead_method(methods))
                fresh = {k: v for k, v in tw.locals.items() if k.startswith("sr_ebi_")}
                tw.locals, tw.values_read = {}, []
                tw.effect("sr_eb_after_click")
                self.assertFalse([v for v in tw.values_read if v.startswith(("sr_eb_margin_", "sr_eb_profit_",
                                                                             "sr_eb_price_", "sr_eb_yardstick"))])
                for k in [f"sr_ebi_p_{p}" for p in eg.PLACES] + ["sr_ebi_yard", "sr_ebi_margin", "sr_ebi_p_over"]:
                    self.assertAlmostEqual(tw.locals[k], fresh[k], delta=2, msg=k)
        tw = Twin()
        tw.effect("sr_eb_count_methods")
        self.assertEqual(unfx(tw.vars["sr_eb_lead_method"]), -1)
        self.assertEqual(eg.lead_method({}), -1)
        self.assertEqual(eg.lead_method({pms[0]: 5, pms[1]: 5}), 0)

    def test_the_totals_formula(self):
        """eg.totals by hand: 150 Asteroid Mine levels, 130 at 16 Psyche and 20 past the
        room, at base prices."""
        state = eg.BaseState(at={"psyche": 130}, over=20)
        got = eg.totals(state, ASTEROID, {})
        for g in eg.GOODS:
            want = eg.BASKET[g] * (130 * (1 + eg.score("psyche", g)) + 20 * 0.25)
            self.assertAlmostEqual(got[g], want, places=6)
        self.assertAlmostEqual(got["profit"], 130 * eg.profit_a_level("psyche", ASTEROID, {}) + 20 * 0.25 * YARD,
                               places=3)
        self.assertAlmostEqual(eg.yardstick(ASTEROID), YARD, delta=0.01)

    def _notice_twin(self, *, src, dst, carried, levels, month, manual=False, is_ai=False, last=None, next_month=None,
                     prices=None):
        tw = _month_twin(_state({src: 10}), room={src: 100, dst: 100}, serves={src: True, dst: True}, built=levels,
                         profit={}, yard=YARD, month_index=month)
        tw.is_ai = is_ai
        for g, r in (prices or {}).items():
            tw.price(g, r)
        tw.vars.update({"sr_eb_move_from": fx(eg.PLACES.index(src)), "sr_eb_move_to": fx(eg.PLACES.index(dst)),
                        "sr_eb_move_carried": fx(carried)})
        if manual:
            tw.vars["sr_eb_manual"] = SCALE
        if last:
            tw.vars["sr_eb_notice_ft"], tw.vars["sr_eb_notice_tt"] = (fx(eg.TYPES.index(t)) for t in last)
        if next_month is not None:
            tw.vars["sr_eb_notice_next"] = fx(next_month)
        tw.effect("sr_eb_move_notice")
        return tw

    def test_the_notice_is_the_model_s(self):
        """eg.notice_due on its edges: the 5% threshold (7 of 140 fires, 6 doesn't), a
        same-type move, the last notice's pair, the year's wait; never for the player's
        own moves or an AI. The good it names is eg.notice_good's, and its record is
        kept for the next."""
        rng = random.Random(75)
        cases = []
        for carried in (6, 7, 8):
            for last in (None, ("metallic", "carbonaceous"), ("carbonaceous", "metallic")):
                for next_month in (None, 24005, 24006):
                    cases.append(dict(src="psyche", dst="ceres", carried=carried, levels=140, month=24005, last=last,
                                      next_month=next_month))
        cases += [dict(src="vesta", dst="valles_marineris", carried=50, levels=140, month=24005),
                  dict(src="near_earth", dst="titan", carried=50, levels=140, month=24005),
                  dict(src="psyche", dst="ceres", carried=50, levels=140, month=24005, manual=True),
                  dict(src="psyche", dst="ceres", carried=50, levels=140, month=24005, is_ai=True)]
        for _ in range(30):
            src, dst = rng.sample(eg.PLACES, 2)
            cases.append(dict(src=src, dst=dst, carried=rng.randint(1, 30), levels=rng.randint(20, 400), month=24005,
                              prices={g: rng.uniform(-0.6, 0.9) for g in eg.GOODS}))
        for c in cases:
            with self.subTest(**{k: v for k, v in c.items() if k != "prices"}):
                tw = self._notice_twin(**c)
                due = (not c.get("manual") and not c.get("is_ai")
                       and eg.notice_due(c["src"], c["dst"], carried=c["carried"], levels=c["levels"], month=c["month"],
                                         last_types=c.get("last"), next_month=c.get("next_month")))
                self.assertEqual(tw.notifications, ["sr_ebase_move_notice"] if due else [])
                if due:
                    rel = {g: round(r, 5) for g, r in (c.get("prices") or {}).items()}
                    self.assertEqual(eg.GOODS[int(unfx(tw.vars["sr_eb_notice_good"]))], eg.notice_good(c["src"], c["dst"], rel))
                    self.assertEqual([unfx(tw.vars[f"sr_eb_notice_{x}"]) for x in ("from", "to", "ft", "tt", "next")],
                                     [eg.PLACES.index(c["src"]), eg.PLACES.index(c["dst"]),
                                      eg.TYPES.index(eg.GROUND[c["src"]]), eg.TYPES.index(eg.GROUND[c["dst"]]),
                                      c["month"] + eg.NOTICE_GAP_MONTHS])
        self.assertEqual(eg.notice_good("psyche", "ceres", {"glass": 0.5}), "glass")

    def test_the_notice_through_the_months(self):
        """150 levels moving from 16 Psyche to Ceres: the notice goes out once the move has
        carried 8 (5% is 7.5), once; a move back within the year tells nothing; after
        the year it does."""
        kw = dict(room=TWO_SITES, serves=BOTH, yard=YARD)
        flipped = {"psyche": SKETCH["ceres"], "ceres": SKETCH["psyche"]}
        vars_, posted = None, []
        for m in range(30):
            profit = SKETCH if m < 10 else flipped
            tw = _month_twin(_state({"psyche": 150}), vars_=vars_, built=150, month_index=24000 + m, profit=profit, **kw)
            tw.effect("sr_eb_month")
            tw.effect("sr_eb_move_notice")
            posted += [24000 + m] * len(tw.notifications)
            vars_ = tw.vars
        # Psyche to Ceres moves 4 a month from 24000: 8 carried at 24001. Ceres back to
        # Psyche from 24010 (40 levels to move), carried 8 by 24011, waits for 24013.
        self.assertEqual(posted, [24001, 24013])


# ---------------------------------------------------------------------------
# Task 9 (second half): a place's name from its index
# ---------------------------------------------------------------------------

CUSTOM = _strip(_raw(str(ge.CUSTOM_LOC_OUT)))


def _entries(name_):
    body = _block(CUSTOM, name_)
    texts = re.findall(r"text = \{\s*(?:trigger = \{([^{}]*)\}\s*)?localization_key = (\w+)\s*\}", body)
    out = []
    for trigger, key in texts:
        m = re.fullmatch(r"\s*has_variable = (\w+)\s*var:(\w+) = (-?\d+)\s*", trigger) if trigger else None
        if trigger:
            assert m and m.group(1) == m.group(2), trigger
        out.append((m.group(1) if m else None, int(m.group(3)) if m else None, key))
    return out


class CustomLocTest(unittest.TestCase):
    def test_custom_loc_names_every_place(self):
        """The contract's names: 41 entries keyed by index, 0 to 40, each naming its place,
        then the fallback; the next place's has -1 past the room."""
        for name_, var in (("sr_eb_place_move_from", "sr_eb_move_from"), ("sr_eb_place_move_to", "sr_eb_move_to"),
                           ("sr_eb_place_last_from", "sr_eb_last_from"), ("sr_eb_place_last_to", "sr_eb_last_to"),
                           ("sr_eb_place_next", "sr_ebase_next_place"),
                           ("sr_eb_place_notice_from", "sr_eb_notice_from"), ("sr_eb_place_notice_to", "sr_eb_notice_to")):
            with self.subTest(name=name_):
                entries = _entries(name_)
                places = [(v, i, k) for v, i, k in entries if i is not None and i >= 0]
                self.assertEqual(places, [(var, i, f"sr_site_name_{k}") for i, k in enumerate(eg.PLACES)])
                self.assertEqual(entries[-1], (None, None, "sr_eb_place_unknown"))
                self.assertEqual([e for e in entries if e[1] is not None and e[1] < 0],
                                 [(var, -1, "sr_eb_place_past_room")] if var == "sr_ebase_next_place" else [])
        short = _entries("sr_eb_place_next_short")
        self.assertEqual([k for _, i, k in short if i is not None and i >= 0],
                         ["sr_site_short_near_earth"] + [gss.overview_name_key(SITES[k]) for k in eg.PLACES[1:]])
        self.assertEqual([k for _, i, k in _entries("sr_eb_place_next_type") if i is not None],
                         [f"sr_ground_{eg.GROUND[k]}" for k in eg.PLACES])
        self.assertEqual([k for _, i, k in _entries("sr_eb_notice_good_name") if i is not None], list(eg.GOODS))
        self.assertEqual(eg.PLACES[0], "near_earth")
        self.assertEqual([s.index for s in sorted(gss.SITES, key=lambda s: s.index)], list(range(1, 41)))

    def test_every_key_the_custom_loc_names_has_loc(self):
        """The mod's loc or vanilla's (Gold is vanilla's name)."""
        import glob
        import json
        with open(os.path.join(REPO, "vanilla_parsed", "localization_english.json"), encoding="utf-8") as f:
            loc = set(dict(json.load(f)))
        for path in glob.glob(os.path.join(REPO, "localization", "english", "**", "*.yml"), recursive=True):
            loc |= set(re.findall(r"(?m)^ ([\w.]+):\d*", open(path, encoding="utf-8-sig").read()))
        for key in sorted(set(re.findall(r"localization_key = (\w+)", CUSTOM))):
            with self.subTest(key=key):
                self.assertIn(key, loc)

    def test_the_base_room_cell_names_the_next_place(self):
        """§ 9.3: the cell's third line names the next place (the overview's short
        form), or reads -75% live past the room; its hover gives the place's type, grade
        and profit a level."""
        loc = {}
        for path in ("te_journal_entries_l_english.yml",):
            loc.update(re.findall(r'(?m)^ ([\w.]+):\d* "(.*)"$', _raw("localization", "english", path)))
        self.assertEqual(loc["je_space_race_widget_ovc_ebase_fig"], "[Country.GetCustom('sr_eb_place_next_short')]")
        self.assertNotIn("je_space_race_widget_ovc_ebase_fig_plus", loc)
        nxt = loc["je_space_race_widget_ovc_ebase_tt_next"]
        for read in ("GetCustom('sr_eb_place_next')", "GetCustom('sr_eb_place_next_type')",
                     "ScriptValue('sr_disp_ebase_next_grade')", "ScriptValue('sr_disp_ebase_next_profit')"):
            with self.subTest(read=read):
                self.assertIn(read, nxt)
        self.assertNotIn("best room first", loc["je_space_race_widget_ovc_ebase_tt"])
        display = _strip(_raw("common", "script_values", "space_race_display_values.txt"))
        self.assertIn("if = { limit = { sr_ebase_queued_levels >= sr_ebase_room_total } value = 1 }",
                      _block(display, "sr_disp_ebase_next_past"))
        self.assertIn("value = var:sr_ebase_next_profit", _block(display, "sr_disp_ebase_next_profit"))

    def test_the_next_place_s_figures(self):
        """sr_eb_next_place stores the next place's profit a level beside its grade: the
        place's own, or past the room a Mixed level's at -75%."""
        rng = random.Random(93)
        for case in range(20):
            room = {p: rng.choice((0, 50, 100)) for p in rng.sample(eg.PLACES, 5)}
            tw = _market_twin(eg.BaseState(), room=room, built=rng.randint(0, 250), queued=rng.randint(0, 50),
                              prices={g: rng.uniform(-0.5, 0.5) for g in eg.method_goods()},
                              logistics={"pm_space_mine": tuple(eg.input_cuts())[:case % 3]})
            tw.effect("sr_eb_month")
            tw.effect("sr_eb_next_place")
            k = int(unfx(tw.vars["sr_ebase_next_place"]))
            with self.subTest(case=case, next=k):
                if k < 0:
                    want = eg.margin("mixed", tw.shares, tw.rel, tw.cuts) * (1 + eg.OVERFLOW_GRADE)
                else:
                    want = eg.profit_a_level(eg.PLACES[k], tw.shares, tw.rel, tw.cuts)
                self.assertAlmostEqual(unfx(tw.vars["sr_ebase_next_profit"]), want, delta=0.05)

    def test_the_room_modifiers_say_the_new_rule(self):
        concepts = _raw("localization", "english", "te_concepts_l_english.yml")
        for key in ("sr_ebase_room_bonus_desc", "sr_ebase_room_penalty_desc"):
            with self.subTest(key=key):
                text = re.search(rf'(?m)^ {key}:\d* "(.*)"$', concepts).group(1)
                self.assertNotIn("richest first", text)
                self.assertIn("Bases view", text)


if __name__ == "__main__":
    unittest.main()
