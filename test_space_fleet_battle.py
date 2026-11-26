"""Space fleets' battles settled on contact (2026-11-25 design § 2,
docs/superpowers/specs/2026-11-25-space-fleet-clock-and-battles-design.md), run
from the script files as they are.

_FxWorld is test_space_fleets._Fx with countries: every_in_global_list and
any_in_global_list over a list of them, has_war_with = prev, is_player, a
while with the engine's 1,000-pass stop, and stand-ins for what reads the map
(buildings, colonies, docks, the legs' tables), each named in its fixture. The
arithmetic is the engine's fixed point, cut toward zero, as _Fx's.
"""

from __future__ import annotations

import re
import unittest
from contextlib import contextmanager
from decimal import Decimal

from test_space_fleets import (COMBAT_EFFECTS, ROOT, _Fx, _FX_SCALE, _fx_top_raw, _fxn, _raw)

PERS_EFFECTS = ROOT / "common/scripted_effects/sr_space_forces_effects.txt"
CODE = {"earth": 1, "inner": 2, "mars": 3}


class _FxWorld(_Fx):
    STUBS = ("sr_loc_rebuild",)

    def __init__(self, tags, wars=(), players=(), values=None, triggers=None):
        super().__init__()
        self.effects = {**self.effects, **_fx_top_raw(_raw(COMBAT_EFFECTS)), **_fx_top_raw(_raw(PERS_EFFECTS))}
        self.tags = list(tags)
        self.world = {t: {} for t in self.tags}
        self.stack = []
        self.wars = {frozenset(w) for w in wars}
        self.players = set(players)
        # What reads the map, per country: (pattern, fn(tag, name)).
        self.ov_values = [(r"sr_fleet_quality|sr_fleet_readiness|sr_pers_share_value", lambda t, n: 1),
                          (r"sr_pers_per_point", lambda t, n: 100),
                          (r"te_history_month_index", lambda t, n: 25000)]
        self.ov_values = list((values or {}).items()) + self.ov_values + [(r"sr_fl_\d_leg_quarters_\w+", lambda t, n: 5)]
        # Unless a test says otherwise: no colony, dock or hostile world, no
        # battlestation or battery, and no leg a fleet may take.
        self.ov_triggers = [(r"sr_loc_held_\w+|sr_loc_port_\w+|sr_fl_\d_has_hostile_world|sr_battlestation_held|sr_has_battery"
                             r"|sr_fl_\d_may_depart_\w+", lambda t, n: False)]
        self.ov_triggers = list((triggers or {}).items()) + self.ov_triggers
        self.vars = {}
        self.events, self.dispatched, self.debris = [], [], []
        self.global_values = {}
        self.saved = {}

    # -- fixtures --------------------------------------------------------------
    def fleet(self, tag, n, loc, drive=1, posture=1, avoid=False, **roles):
        """Slot n of tag at loc, each role (now, full) or now."""
        v = self.world[tag]
        v[f"sr_fl_{n}_loc"] = _fxn(CODE[loc])
        total = 0
        for k, x in roles.items():
            now, full = x if isinstance(x, tuple) else (x, x)
            v[f"sr_fl_{n}_{k}"], v[f"sr_fl_{n}_{k}_full"] = _fxn(now), _fxn(full)
            total += now
        v[f"sr_fl_{n}_drive"] = _fxn(drive)
        v[f"sr_fl_{n}_posture"] = _fxn(posture)
        if avoid:
            v[f"sr_fl_{n}_avoid"] = _FX_SCALE
        # What sr_loc_rebuild sets (stubbed): the country's strength there.
        v[f"sr_fl_at_{loc}"] = v.get(f"sr_fl_at_{loc}", 0) + _fxn(total)

    def strength(self, tag, n):
        with self._in(tag):
            return Decimal(self.num(f"sr_fl_{n}_strength")) / _FX_SCALE

    def var(self, tag, name):
        x = self.world[tag].get(name)
        return None if x is None else Decimal(x) / _FX_SCALE

    def battle(self, loc):
        self.locals = {}
        self.run([("sr_battle_at", "=", [("LOC", "=", loc), ("CODE", "=", str(CODE[loc]))])])

    # -- the engine, with countries -------------------------------------------
    @contextmanager
    def _in(self, tag):
        saved = self.vars
        self.stack.append(tag)
        self.vars = self.world[tag]
        try:
            yield
        finally:
            self.stack.pop()
            self.vars = saved

    def _here(self):
        return self.stack[-1] if self.stack else None

    def num(self, v):
        if isinstance(v, str):
            for pat, fn in self.ov_values:
                if re.fullmatch(pat, v):
                    return _fxn(fn(self._here(), v))
        return super().num(v)

    def calc(self, block, acc=0):
        out = []
        for item in block:
            key, _, v = item
            if key == "every_in_global_list":
                if out:
                    acc, out = super().calc(out, acc), []
                lim = next((x for k, _, x in v if k == "limit"), [])
                body = [e for e in v if e[0] not in ("variable", "limit")]
                for t in self.tags:
                    with self._in(t):
                        if self.test(lim):
                            acc = self.calc(body, acc)
            else:
                out.append(item)
        return super().calc(out, acc) if out else acc

    def cond(self, key, op, v):
        for pat, fn in self.ov_triggers:
            if re.fullmatch(pat, key):
                got = fn(self._here(), key)
                return got == (v == "yes") if v in ("yes", "no") else got
        if key == "has_war_with":
            other = self.saved[v[len("scope:"):]] if v.startswith("scope:") else self.stack[-2]
            assert v == "prev" or v.startswith("scope:"), v
            return frozenset((self.stack[-1], other)) in self.wars
        if key == "is_country_alive":
            return v == "yes"
        if key == "is_player":
            return (self._here() in self.players) == (v == "yes")
        if key == "has_local_variable":
            return v in self.locals
        if key == "any_in_global_list":
            lim = [e for e in v if e[0] != "variable"]
            for t in self.tags:
                with self._in(t):
                    if self.test(lim):
                        return True
            return False
        return super().cond(key, op, v)

    def run(self, block):
        taken = False
        for key, op, v in block:
            if key in ("if", "else_if", "else"):
                taken = False if key == "if" else taken
                if taken or (key != "else" and not self.test(next(x for k, _, x in v if k == "limit"))):
                    continue
                taken = True
                self.run([e for e in v if e[0] != "limit"])
            elif key == "every_in_global_list":
                lim = next((x for k, _, x in v if k == "limit"), [])
                body = [e for e in v if e[0] not in ("variable", "limit")]
                for t in self.tags:
                    with self._in(t):
                        if self.test(lim):
                            self.run(body)
            elif key == "while":
                lim = next(x for k, _, x in v if k == "limit")
                body = [e for e in v if e[0] != "limit"]
                passes = 0
                while self.test(lim):
                    passes += 1
                    assert passes <= 1000, "the engine stops a while at 1,000 passes"
                    self.run(body)
            elif key == "trigger_event":
                self.events.append((self._here(), dict((k, x) for k, _, x in v)))
            elif key == "sr_fl_dispatch":
                self.dispatched.append((self._here(), dict((k, x) for k, _, x in v)))
            elif key == "save_temporary_scope_as":
                self.saved[v] = self._here()
            elif key == "te_debris_add":
                self.debris.append({k: self.num(x) for k, _, x in v})
            elif key == "set_global_variable":
                d = {k: x for k, _, x in v}
                self.globals.add(d["name"])
                self.global_values[d["name"]] = self.num(d["value"])
            elif key == "debug_log":
                self.logs.append((v, dict(self.global_values)))
            else:
                super().run([(key, op, v)])


def _two(**kw):
    """Two countries at war, A and B."""
    return _FxWorld(("A", "B"), wars=[("A", "B")], **kw)


def _always(*tags_names):
    """A trigger stand-in that holds for these (tag, name pattern) pairs."""
    return lambda t, n: any(t == tag and re.fullmatch(pat, n) for tag, pat in tags_names)


class EvenFightTest(unittest.TestCase):
    """Two equal fleets at Mars, both engaging: the square law in steps of
    sr_bt_k until each has lost half of what it brought (§ 2.4, an even fight
    breaks in about 14 steps), within the tick."""

    def setUp(self):
        self.w = _two(values={r"sr_fl_\d_leg_quarters_\w+": lambda t, n: 5},
                      triggers={r"sr_fl_\d_may_depart_earth": lambda t, n: True})
        self.w.fleet("A", 1, "mars", war=100)
        self.w.fleet("B", 1, "mars", posture=2, war=100)
        self.w.battle("mars")

    def test_both_break_at_half_in_about_fourteen_steps(self):
        for tag in "AB":
            with self.subTest(country=tag):
                self.assertLessEqual(self.w.strength(tag, 1), 50)
                self.assertGreater(self.w.strength(tag, 1), 40)
        self.assertGreaterEqual(self.w.locals["sr_bt_steps"], _fxn(12))
        self.assertLessEqual(self.w.locals["sr_bt_steps"], _fxn(16))

    def test_each_broken_fleet_leaves_for_the_nearest_dock(self):
        self.assertEqual(sorted((t, d["N"], d["LOC"]) for t, d in self.w.dispatched), [("A", "1", "earth"), ("B", "1", "earth")])

    def test_the_battle_figures_are_cleared(self):
        for tag in "AB":
            left = [k for k in self.w.world[tag] if "_bt_" in k or k.startswith("sr_bt_")]
            self.assertEqual(left, [], tag)

    def test_war_support_and_the_stamp(self):
        for tag in "AB":
            # Equal shares lost: neither's is larger, so each reads it lost.
            self.assertEqual(self.w.var(tag, "sr_ws_battle"), Decimal("-0.1"))
        self.assertIn("sr_loc_battle_mars", self.w.globals)
        self.assertEqual(self.w.debris, [])   # debris only at Earth

    def test_the_self_check_logs_ok(self):
        self.assertIn("sr_bt_ok_logged", self.w.globals)
        self.assertTrue(any("TE_SELF_CHECK OK fleet_battle" in line for line, _ in self.w.logs))


class UnevenFightTest(unittest.TestCase):
    """2:1: the weaker breaks, the stronger stays and pays about a tenth (§ 3)."""

    def test_two_to_one(self):
        w = _two(values={r"sr_fl_\d_leg_quarters_\w+": lambda t, n: 5},
                 triggers={r"sr_fl_\d_may_depart_earth": lambda t, n: True})
        w.fleet("A", 1, "mars", war=200)
        w.fleet("B", 1, "mars", posture=2, war=100)
        w.battle("mars")
        self.assertLessEqual(w.strength("B", 1), 50)
        # About a tenth (§ 3): the continuous square law's 9.9%, 11.4% in steps of 0.05.
        self.assertGreater(w.strength("A", 1), 176)
        self.assertEqual([(t, d["N"]) for t, d in w.dispatched], [("B", "1")])
        self.assertEqual(w.var("A", "sr_ws_battle"), Decimal("0.1"))
        self.assertEqual(w.var("B", "sr_ws_battle"), Decimal("-0.1"))

    def test_the_square_law_shares_fire_by_strength(self):
        """A against B and C, its allies' enemies but not at war with each
        other: A's fire splits between them by strength, theirs all on A."""
        w = _FxWorld(("A", "B", "C"), wars=[("A", "B"), ("A", "C")])
        w.fleet("A", 1, "mars", war=100)
        w.fleet("B", 1, "mars", posture=2, war=60)
        w.fleet("C", 1, "mars", posture=2, war=20)
        # One step by hand: the setup and the first step of sr_battle_run.
        w.locals = {}
        w.run([("set_local_variable", "=", [("name", "=", "sr_cb_code"), ("value", "=", "3")])])
        for t in "ABC":
            with w._in(t):
                w.run(_parse("set_variable = { name = sr_bt_before value = 0 } set_variable = { name = sr_bt_lost value = 0 } "
                             "set_variable = { name = sr_bt_dead value = 0 } set_variable = { name = sr_bt_present value = yes } "
                             "set_local_variable = { name = sr_bt_held value = 0 } set_local_variable = { name = sr_bt_units value = 0 } "
                             "sr_fl_bt_setup_at = { N = 1 } set_variable = { name = sr_bt_s value = 0 } "
                             "set_variable = { name = sr_bt_f value = 0 } sr_fl_bt_ready_at = { N = 1 }"))
        w.run(_parse("set_local_variable = { name = sr_bt_steps value = 0 } set_local_variable = { name = sr_bt_debris value = 0 } "
                     "set_local_variable = { name = sr_bt_ends value = 0 } set_local_variable = { name = sr_bt_battle value = 0 } "
                     "sr_bt_step = yes"))
        k = Decimal("0.05")
        # A: 100 x k x (60/100 + 20/100) = 4; B: 60 x k x 100/80 = 3.75; C: 20 x k x 100/80 = 1.25.
        self.assertEqual(w.strength("A", 1), 100 - 100 * k * Decimal("0.8"))
        self.assertEqual(w.strength("B", 1), 60 - 60 * k * Decimal("1.25"))
        self.assertEqual(w.strength("C", 1), 20 - 20 * k * Decimal("1.25"))
        # A's fire dealt out exactly: B's and C's losses sum to k x its fire.
        self.assertEqual(80 - w.strength("B", 1) - w.strength("C", 1), 100 * k)


class WhoFightsTest(unittest.TestCase):
    """§ 2.3: both engage, they fight; neither, no battle; one engages: it
    catches the other if at least as fast, or if the other is tied there."""

    def _run(self, a_drive=1, b_drive=1, b_avoid=False, a_avoid=False, b_posture=2, held_b=False, hostile_world_b=False):
        triggers = {}
        if held_b:
            triggers[r"sr_loc_held_mars"] = _always(("B", r"sr_loc_held_mars"))
        if hostile_world_b:
            triggers[r"sr_fl_1_has_hostile_world"] = _always(("B", r"sr_fl_1_has_hostile_world"))
        # Players: an AI would set its own Engage or Avoid (AiTest).
        w = _two(players=["A", "B"], triggers=triggers)
        w.fleet("A", 1, "mars", drive=a_drive, avoid=a_avoid, war=100)
        w.fleet("B", 1, "mars", drive=b_drive, posture=b_posture, avoid=b_avoid, war=100)
        w.battle("mars")
        return w.strength("A", 1) < 100 or w.strength("B", 1) < 100

    def test_the_rule(self):
        cases = {
            "both engage": (dict(), True),
            "neither engages": (dict(a_avoid=True, b_avoid=True), False),
            "a faster avoider gets away": (dict(a_drive=1, b_drive=2, b_avoid=True), False),
            "an avoider no faster is caught": (dict(a_drive=2, b_drive=2, b_avoid=True), True),
            "a slower avoider is caught": (dict(a_drive=2, b_drive=1, b_avoid=True), True),
            "an avoider tied by its colony is caught": (dict(a_drive=1, b_drive=3, b_avoid=True, held_b=True), True),
            "an avoider closing in is caught": (dict(a_drive=1, b_drive=3, b_avoid=True, b_posture=3), True),
            "an avoider interdicting is caught": (dict(a_drive=1, b_drive=3, b_avoid=True, b_posture=4), True),
            "an avoider blockading is caught": (dict(a_drive=1, b_drive=3, b_avoid=True, hostile_world_b=True), True),
            "an avoider standing off elsewhere gets away": (dict(a_drive=1, b_drive=3, b_avoid=True), False),
        }
        for name, (kw, fights) in cases.items():
            with self.subTest(case=name):
                self.assertEqual(self._run(**kw), fights)

    def test_rapid_response_alone_is_a_drive_faster(self):
        # Both torch (2); B all rapid response: pace 3, so it slips A.
        w = _two(players=["A", "B"])
        w.fleet("A", 1, "mars", drive=2, war=100)
        w.fleet("B", 1, "mars", drive=2, avoid=True, rapid=100)
        w.battle("mars")
        self.assertEqual(w.strength("B", 1), 100)


class EarthTest(unittest.TestCase):
    """At Earth everyone is tied; the Orbital Battlestation fights for its
    owner and never breaks; the batteries fire once a tick before the battle."""

    def test_the_battlestation_fights_until_its_strength_is_gone_and_never_breaks(self):
        w = _two(values={r"sr_battlestation_fire": lambda t, n: 50, r"sr_battlestation_full": lambda t, n: 100},
                 triggers={r"sr_battlestation_held": _always(("A", r"sr_battlestation_held"))})
        w.world["A"]["sr_battlestation_strength"] = _fxn(100)
        w.fleet("B", 1, "earth", avoid=True, war=100)
        w.battle("earth")
        # B, at Earth and avoiding, is caught all the same, and breaks.
        self.assertLessEqual(w.strength("B", 1), 50)
        self.assertLess(w.var("A", "sr_battlestation_strength"), 100)
        self.assertGreater(w.var("A", "sr_battlestation_strength"), 0)
        # B was at Earth, a dock: it stays.
        self.assertEqual(w.dispatched, [])
        # Debris at Earth from every point lost.
        self.assertEqual(len(w.debris), 1)

    def test_the_batteries_fire_a_quarter_of_a_month_s(self):
        w = _two(values={r"sr_battery_fire": lambda t, n: 100, r"sr_battery_fire_kinetic": lambda t, n: 40},
                 triggers={r"sr_has_battery": _always(("A", r"sr_has_battery"))})
        w.fleet("B", 1, "earth", war=60)
        w.fleet("B", 2, "earth", war=40)
        w.battle("earth")
        # 100 x 0.1 x 0.25 = 2.5, shared 60:40; no fleet of A's, so no battle.
        self.assertEqual(w.strength("B", 1), Decimal("58.5"))
        self.assertEqual(w.strength("B", 2), Decimal("39"))
        self.assertEqual(w.locals["sr_bt_battle"], 0)
        # Kinetic debris: 40 x 0.25 x sr_battery_debris_low.
        self.assertIn({"LOW": _fxn("0.2"), "HIGH": 0}, w.debris)
        self.assertEqual(w.var("A", "sr_ws_battle"), Decimal("0.1"))

    def test_a_player_hit_by_the_batteries_alone_is_told_once_a_month(self):
        w = _two(players=["B"], values={r"sr_battery_fire": lambda t, n: 100, r"sr_battery_fire_kinetic": lambda t, n: 0},
                 triggers={r"sr_has_battery": _always(("A", r"sr_has_battery"))})
        w.fleet("B", 1, "earth", war=100)
        w.battle("earth")
        self.assertEqual([t for t, e in w.events], ["B"])
        self.assertIn("sr_battery_notice_pending", w.world["B"])
        self.assertNotIn("sr_battle_notice_pending", w.world["B"])


class AiTest(unittest.TestCase):
    """§ 2.7: an AI engages where its strength x fire is at least the enemy's."""

    def test_the_weaker_ai_avoids_and_the_stronger_engages(self):
        w = _two(players=[])
        w.fleet("A", 1, "mars", drive=2, war=100)
        w.fleet("B", 1, "mars", drive=1, war=60)
        w.battle("mars")
        # B, weaker, avoids, but A is faster: caught. A engages.
        self.assertNotIn("sr_fl_1_avoid", w.world["A"])
        self.assertIn("sr_fl_1_avoid", w.world["B"])
        self.assertLess(w.strength("B", 1), 60)

    def test_a_player_s_setting_is_its_own(self):
        w = _two(players=["B"])
        w.fleet("A", 1, "mars", war=100)
        w.fleet("B", 1, "mars", war=10)
        w.battle("mars")
        self.assertNotIn("sr_fl_1_avoid", w.world["B"])


class AiDefendTest(unittest.TestCase):
    """§ 2.7: sr_fl_ai_defend_<loc> on the win test. B's 100 warships are bound
    for Mars, where A holds a colony; A's free fleets at Earth can reach it."""

    def _defend(self, *ours, at_mars=0):
        w = _two(triggers={r"sr_fl_ai_threatened_mars": lambda t, n: True, r"sr_icpt_interdicts_at": lambda t, n: False})
        # A slot's gates hold for a fleet at Earth (as may_depart's own has_variable does).
        w.ov_triggers.insert(0, (r"sr_fl_\d_ai_free|sr_fl_\d_ai_reaches_mars|sr_fl_\d_may_depart_mars",
                                 lambda t, n: w.world[t].get(f"sr_fl_{n[6]}_loc") == _fxn(CODE["earth"])))
        w.fleet("B", 1, "mars", war=100)
        del w.world["B"]["sr_fl_1_loc"]
        w.world["B"]["sr_fl_1_dest"] = _fxn(CODE["mars"])
        for n, strength in enumerate(ours, 1):
            w.fleet("A", n, "earth", war=strength)
        if at_mars:
            w.fleet("A", len(ours) + 1, "mars", war=at_mars)
        with w._in("A"):
            w.locals = {}
            w.run(_parse("sr_fl_ai_defend_mars = yes"))
        return sorted(int(d["N"]) for t, d in w.dispatched)

    def test_the_strongest_alone_if_it_wins(self):
        self.assertEqual(self._defend(150, 60), [1])

    def test_together_if_only_together_they_win(self):
        self.assertEqual(self._defend(60, 60), [1, 2])

    def test_none_if_even_together_they_lose(self):
        self.assertEqual(self._defend(40, 40), [])

    def test_nothing_while_already_winning(self):
        self.assertEqual(self._defend(150, at_mars=120), [])

    def test_more_when_ours_there_would_lose(self):
        # 50 there and 60 free: 110 against 100.
        self.assertEqual(self._defend(60, at_mars=50), [1])


class CeilingTest(unittest.TestCase):
    """Fleets with almost no fire (tenders on tenders) reach the step ceiling
    without settling, and that is no BROKEN: their fire is far below half their
    strength."""

    def test_tenders_reach_the_ceiling_quietly(self):
        w = _two()
        w.fleet("A", 1, "mars", tender=100)
        w.fleet("B", 1, "mars", tender=100)
        w.battle("mars")
        self.assertEqual(w.locals["sr_bt_steps"], _fxn(60))
        self.assertNotIn("sr_bt_broken_logged", w.globals)
        self.assertGreater(w.strength("A", 1), 50)


class WiringTest(unittest.TestCase):
    """§ 2.2: the battle on every tick, after the landings and the location
    records; the siege only on the 1st, after the battle."""

    @classmethod
    def setUpClass(cls):
        from test_space_fleets import FLEET_EFFECTS, _block, _strip
        cls.block = staticmethod(_block)
        cls.fleet = _strip(_raw(FLEET_EFFECTS))
        cls.combat = _strip(_raw(COMBAT_EFFECTS))

    def test_every_tick_fights_after_the_landings(self):
        for name in ("sr_fl_global_month", "sr_fl_tick_step"):
            with self.subTest(step=name):
                body = self.block(self.fleet, name)
                order = ["sr_fl_each_slot = { DO = arrive }", "sr_loc_rebuild = yes", "sr_battle_global_tick = yes",
                         "sr_fl_tick_alerts = yes"]
                idx = [body.index(x) for x in order]
                self.assertEqual(idx, sorted(idx))
        month = self.block(self.fleet, "sr_fl_global_month")
        self.assertLess(month.index("sr_battle_global_tick = yes"), month.index("sr_combat_global_monthly = yes"))
        self.assertNotIn("sr_combat_global_monthly", self.block(self.fleet, "sr_fl_tick_step"))

    def test_every_location_has_its_battle(self):
        tick = self.block(self.combat, "sr_battle_global_tick")
        self.assertEqual(re.findall(r"sr_battle_at = \{ LOC = (\w+) CODE = (\d) \}", tick),
                         [("earth", "1"), ("inner", "2"), ("mars", "3"), ("asteroids", "4"), ("jupiter", "5"),
                          ("saturn", "6"), ("uranus", "7"), ("neptune", "8"), ("kuiper", "9")])

    def test_the_siege_has_no_fleet_against_fleet_losses(self):
        at = self.block(self.combat, "sr_combat_at")
        for gone in ("sr_cb_hostile_r", "sr_cb_e1", "sr_cb_l1", "sr_cb_battle_record", "sr_cb_battery_gather", "sr_fleet_k"):
            self.assertNotIn(gone, at)
        self.assertIn("sr_cb_def_losses_$LOC$ = yes", at)
        self.assertIn("sr_cb_worlds_after_$LOC$ = yes", at)

    def test_the_step_is_bounded(self):
        run = self.block(self.combat, "sr_battle_run")
        self.assertRegex(run, r"while = \{\s*limit = \{\s*local_var:sr_bt_pairs > 0\s*local_var:sr_bt_steps < sr_bt_max_steps")
        values = _raw(ROOT / "common/script_values/sr_fleet_values.txt")
        for name, want in (("sr_bt_k", "0.05"), ("sr_bt_max_steps", "60"), ("sr_bt_break_share", "0.5"),
                           ("sr_battery_tick_share", "0.25"), ("sr_fl_ai_engage_margin", "1")):
            self.assertRegex(values, rf"(?m)^{name} = \{{ value = {re.escape(want)} \}}")

    def test_the_report_is_once_a_tick(self):
        record = self.block(self.combat, "sr_bt_record")
        self.assertIn("set_variable = { name = sr_battle_notice_pending value = yes days = 6 }", record)
        self.assertIn("set_variable = { name = sr_battery_notice_pending value = yes days = 25 }", record)
        self.assertIn("trigger_event = { id = space_race_events.101 days = 1 }", record)


def _parse(text):
    from test_space_fleets import _fx_parse, _fx_tokens
    return _fx_parse(_fx_tokens(text))[0]


if __name__ == "__main__":
    unittest.main()
