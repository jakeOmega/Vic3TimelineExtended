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

    def __init__(self, state, type_="building_space_mine", level=1, pm="pm_space_mine", mods=None):
        self.state, self.type, self.level, self.pms = state, type_, level, {pm} if pm else set()
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
            statics = {}
            for k, v in _top_raw(_raw("common", "static_modifiers", "space_race_modifiers.txt")).items():
                body = _parse(_tokens(v))[0]
                statics[k] = {key: fx(x) for key, _, x in body
                              if isinstance(x, str) and re.fullmatch(r"-?[\d.]+", x)}
            Twin._sources = values, effects, triggers, statics, {}
        self.values, self.effects, self.triggers, self.statics, self._parsed = Twin._sources
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
        return all(self.cond(*c) for c in block)

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
                d = {k: x for k, _, x in v}
                assert self.scope[-1] == "country" or key == "set_local_variable", \
                    f"{key} in {self.scope[-1]}: buildings hold no variables"
                value = SCALE if d.get("value", "yes") == "yes" else self.num(d["value"])
                (self.locals if key == "set_local_variable" else self.vars)[d["name"]] = value
            elif key in ("change_variable", "change_local_variable"):
                d = {k: x for k, _, x in v}
                store = self.locals if key == "change_local_variable" else self.vars
                assert d["name"] in store, f"{key} on {d['name']}, never set"
                assert set(d) <= {"name", "add", "subtract"}, f"{key} with {set(d)}"
                store[d["name"]] += self.num(d["add"]) if "add" in d else -self.num(d["subtract"])
            elif key == "remove_variable":
                assert v in self.vars, f"remove_variable {v}, not set"
                del self.vars[v]
            elif key == "set_global_variable":
                d = {k: x for k, _, x in v} if isinstance(v, list) else {"name": v}
                self.globals[d["name"]] = SCALE if d.get("value", "yes") == "yes" else self.num(d["value"])
            elif key == "add_modifier":
                d = {k: x for k, _, x in v} if isinstance(v, list) else {"name": v}
                mult = self.num(d["multiplier"]) if "multiplier" in d else SCALE
                self._mods().setdefault(d["name"], []).append(mult)
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
                named = set(re.findall(r"multiply = sr_eb_levels_(\w+)", body))
                self.assertEqual(named, mining)
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
                    terms = re.findall(rf"add = 1 multiply = (-?[\d.]+) multiply = sr_eb_levels_{pm} }}", body)
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
                self.assertIn(f"add = {{ value = sr_eb_levels_{pm} multiply = "
                              f"{ge.num(eg.margin('mixed', {pm: 1.0}, {}))} }}", yard)
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
            for n, (pm, lv) in enumerate(levels.items()):
                if lv:
                    tw.buildings.append(Building(n, level=lv, pm=pm))
            tw.buildings.append(Building(9, level=7, pm="pm_space_colony_vacation"))  # outside the seven goods
            prices = {g: rng.uniform(-0.75, 1.5) for g in eg.method_goods()}
            for g, r in prices.items():
                tw.price(g, r)
            tw.effect("sr_eb_count_methods")
            total = sum(levels.values())
            shares = {pm: lv / total for pm, lv in levels.items() if lv}
            rel = {g: round(r, 5) for g, r in prices.items()}
            for k in ("near_earth", "psyche", "ceres", "io", "titan", "ganymede", "vesta", "sedna"):
                with self.subTest(trial=trial, place=k):
                    self.assertAlmostEqual(unfx(tw.num(f"sr_eb_profit_{k}")), eg.profit_a_level(k, shares, rel),
                                           delta=0.05)
            self.assertAlmostEqual(unfx(tw.num("sr_eb_yardstick")), eg.yardstick(shares), delta=0.05)
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
        for call in ("sr_eb_count_methods", "sr_eb_fill_by_grade", "sr_eb_compute_mix", "sr_eb_apply_mix"):
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


class TodayOrderTest(unittest.TestCase):
    """Task 5's order (§ 4): the levels fill the room serving us best grade first, and
    T and D(g) are the model's mix_now for those counts."""

    def _fill(self, rooms, built, blockaded=()):
        tw = _twin_base(built=built, rooms=rooms, blockaded=blockaded)
        tw.effect("sr_eb_fill_by_grade")
        tw.effect("sr_eb_compute_mix")
        return tw

    def test_fill_and_mix_match_the_model(self):
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
                tw = self._fill(rooms, built, blockaded)
                state = eg.BaseState()
                serves = {p: p not in blockaded for p in rooms}
                state = eg.month(state, room=rooms, serves=serves, held={p: True for p in rooms}, built=built,
                                 profit={}, yard=7250)
                self.assertEqual(tw.counts("sr_eb_at_"), state.at)
                self.assertEqual(unfx(tw.vars["sr_eb_over"]), state.over)
                t, d = eg.mix_now(state)
                self.assertAlmostEqual(unfx(tw.vars["sr_ebase_grade"]), 100 * t, delta=1e-4)
                for g in eg.GOODS:
                    self.assertAlmostEqual(unfx(tw.vars[f"sr_ebase_mix_{g}"]), 100 * d[g], delta=2e-4, msg=g)
                    self.assertEqual(tw.vars[f"sr_ebase_mix_{g}_units"], abs(tw.vars[f"sr_ebase_mix_{g}"]))

    def test_one_type_base_carries_the_type_mix(self):
        tw = self._fill({"vesta": 100, "valles_marineris": 50, "daedalus": 30, "mercury": 7}, 187)
        for g in eg.GOODS:
            with self.subTest(good=g):
                self.assertAlmostEqual(unfx(tw.vars[f"sr_ebase_mix_{g}"]), 100 * eg.mix("rocky")[g], delta=2e-4)

    def test_no_levels_no_mix(self):
        tw = self._fill({"psyche": 300}, 0)
        self.assertEqual(tw.vars["sr_ebase_grade"], 0)
        self.assertEqual({g: tw.vars[f"sr_ebase_mix_{g}"] for g in eg.GOODS}, {g: 0 for g in eg.GOODS})

    def test_next_grade_is_kept_for_the_cell(self):
        """var:sr_ebase_next_grade stays until Task 9's Base Room cell stops reading it."""
        for queued, want in ((150, 30), (300, 15), (500, gss.OVERFLOW_GRADE)):
            with self.subTest(queued=queued):
                tw = _twin_base(built=150, rooms={"psyche": 300, "ceres": 200}, queued=queued)
                tw.effect("sr_ebase_next_fill")
                self.assertEqual(unfx(tw.vars["sr_ebase_next_grade"]), want)


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

    def test_the_self_check_row(self):
        playtest = _raw("docs", "testing", "solar-colonies-playtest.md")
        self.assertIn("`TE_SELF_CHECK OK/BROKEN ebase_mix", playtest)


if __name__ == "__main__":
    unittest.main()
