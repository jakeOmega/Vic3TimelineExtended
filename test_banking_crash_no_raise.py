"""A crash can never raise the banking cycle's value or momentum.

`apply_banking_crash_origin_effects` used to `set_variable` the cycle to a fixed
figure per severity tier (value 40 and momentum -1 for a "Market Correction").
A country already below the figure, say a Downturn at cycle 12 with momentum
-3.5, was lifted by the crash. The contagion roll reaches countries at any cycle
value, so it was not rare, and the engine says nothing about it. The softening
responses then added up to +12 on top, and the contagion scare's floor clamps
(cycle 5, momentum -5) pulled a country that was already under them back up.

The rule now: the tier figures are ceilings, and every option that adds to or
clamps either figure is bracketed by `banking_crash_note_prior_state` /
`banking_crash_hold_to_prior_state`, which puts a figure back to its pre-crash
level if the option left it higher.

This runs the real script, not a copy of it. It is deliberately a small
interpreter, not an engine emulator: syntax it does not model fails, and a
scripted effect it does not model is ignored only if nothing it reaches writes
the cycle's two variables. Every option of `minor_events_timelineextended.6`
(the origin crash) and `.7` (contagion) runs over a grid of cycle states, so a
new option with a raw `change_variable` on either figure fails here.
"""
import copy
import itertools
import operator
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
CYCLE_VARS = ("finance_cycle_value", "finance_cycle_momentum")
PRIOR_VARS = ("banking_crash_prior_value", "banking_crash_prior_momentum")
EPS = 1e-9

# Engine effects that never touch a variable, so an option may use them freely.
INERT_EFFECTS = {"add_radicals", "add_modifier", "remove_modifier", "add_treasury"}
# Keys of an option block that are not effects.
OPTION_META = {"name", "default_option", "trigger", "ai_chance"}


def parse_body(source):
    tokens = iter(ParadoxFileParser().tokenize(source))

    def body():
        result = []
        for key in tokens:
            if key == "}":
                return result
            op = next(tokens)
            value = next(tokens)
            result.append((key, op, body() if value == "{" else value.strip('"')))
        return result
    return body()


def definitions(path):
    text = (ROOT / path).read_text(encoding="utf-8-sig")
    return {key: value for key, _, value in parse_body(text)}


def field(body, name):
    return next(val for key, _, val in body if key == name)


def substitute(node, params):
    """A copy of ``node`` with every ``$NAME$`` replaced, as the engine does for a call."""
    if isinstance(node, list):
        return [(k, op, substitute(v, params)) for k, op, v in node]
    for name, value in params.items():
        node = node.replace(f"${name}$", str(value))
    return node


class Registry:
    """Every scripted effect, parsed a file at a time on first use."""

    def __init__(self):
        self.files = {}
        self.parsed = {}
        self.writes = {}
        top = re.compile(r"^([A-Za-z_][\w.]*)[ \t]*=[ \t]*\{", re.M)
        for path in sorted((ROOT / "common" / "scripted_effects").glob("*.txt")):
            for name in top.findall(path.read_text(encoding="utf-8-sig")):
                self.files.setdefault(name, path)

    def __contains__(self, name):
        return name in self.files

    def body(self, name):
        path = self.files[name]
        if path not in self.parsed:
            self.parsed[path] = definitions(path.relative_to(ROOT))
        return self.parsed[path][name]

    def writes_cycle(self, name, seen=()):
        """Whether the effect, or anything it calls, writes the cycle's variables."""
        if name not in self.writes:
            self.writes[name] = self._walk(self.body(name), (*seen, name))
        return self.writes[name]

    def _walk(self, body, seen):
        for key, _, val in body:
            if key in ("set_variable", "change_variable") and isinstance(val, list):
                if field(val, "name") in CYCLE_VARS:
                    return True
            if isinstance(val, list) and self._walk(val, seen):
                return True
            if key in self and key not in seen and self.writes_cycle(key, seen):
                return True
        return False


REGISTRY = Registry()
EFFECTS = definitions("common/scripted_effects/banking_cycle_effects.txt")
MINOR_EVENTS = definitions("events/minor_events.txt")
TRIGGERS = definitions("common/scripted_triggers/banking_policy_triggers.txt")


class Interp:
    def __init__(self, variables, laws=(), scopes=(), global_vars=(), overrides=None, values=None,
                 global_values=None, picks=None, others=None, trigger_values=None):
        self.vars = dict(variables)
        self.laws = set(laws)
        self.globals = set(global_vars)
        self.logs = []
        # Saved scopes, name -> the scope saved: "ROOT" for the event's own country, any other
        # name for another country. Event .7 saves its own roll as contagion_crashed = ROOT; a
        # cascade's target inherits the upstream country's. A bare name means ROOT.
        self.scopes = dict(scopes) if isinstance(scopes, dict) else dict.fromkeys(scopes, "ROOT")
        self.tooltips = []
        # Scripted effects replaced by a test: name -> the body run instead (None runs nothing).
        # Each call is recorded in ``ran``. Mutation tests replace a real effect the same way.
        self.overrides = dict(overrides or {})
        self.ran = []
        # Named script values a test pins (this_country_gdp_value), and global variables' values.
        self.values = dict(values or {})
        self.global_values = dict(global_values or {})
        self.events = []  # every trigger_event, as {field: value}
        # random_list: the entry each one takes, by position, in order; a random_list with no pick
        # left fails, so a test states every roll it expects.
        self.picks = picks if picks is not None else []
        # Variables of the other countries a `scope:x = { ... }` trigger reads, by saved-scope name.
        self.others = dict(others or {})
        # Scripted triggers from outside banking_policy_triggers.txt that a test pins, name -> bool.
        self.trigger_values = dict(trigger_values or {})

    def num(self, token):
        if isinstance(token, list):  # an inline script value: value, then arithmetic in order
            n = 0.0
            for op, _, arg in token:
                x = self.num(arg)
                n = {"value": x, "add": n + x, "subtract": n - x, "multiply": n * x,
                     "divide": n / x if x else n, "min": max(n, x), "max": min(n, x)}[op]
            return n
        if token.startswith("var:"):
            return float(self.vars.get(token[4:], 0))  # an unrecorded var: reads 0
        if token in self.values:
            return float(self.values[token])
        return float(token)

    def check(self, body, mode="AND"):
        answers = []
        for key, op, val in body:
            if key in ("AND", "OR", "NOT"):
                answer = self.check(val, key)
            elif key == "has_variable":
                answer = val in self.vars
            elif key == "has_global_variable":
                answer = val in self.globals
            elif key == "has_law":
                answer = val.removeprefix("law_type:") in self.laws
            elif key == "exists" and val.startswith("scope:"):
                answer = val.removeprefix("scope:") in self.scopes
            elif key in ("root", "ROOT") and val.startswith("scope:"):
                answer = self.scopes.get(val.removeprefix("scope:")) == "ROOT"
            elif key.startswith("scope:") and isinstance(val, list):
                answer = Interp(self.others.get(key.removeprefix("scope:"), {})).check(val)
            elif key in self.trigger_values:
                answer = self.trigger_values[key] == (val == "yes")
            elif key in TRIGGERS and val == "yes":
                answer = self.check(TRIGGERS[key])
            elif key.startswith("var:"):
                answer = {"=": operator.eq, ">": operator.gt, "<": operator.lt,
                          ">=": operator.ge, "<=": operator.le}[op](self.num(key), self.num(val))
            else:
                raise AssertionError(f"unmodelled trigger {key}")
            answers.append(answer)
        if mode == "NOT":
            return not any(answers)
        return any(answers) if mode == "OR" else all(answers)

    def execute(self, body):
        chain_done = False
        for key, _, val in body:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    chain_done = False
                run = not chain_done and (key == "else" or self.check(field(val, "limit")))
                if run:
                    chain_done = True
                    self.execute([item for item in val if item[0] != "limit"])
                continue
            if key == "hidden_effect":
                self.execute(val)
            elif key == "custom_tooltip":
                if isinstance(val, list):
                    self.tooltips.append(field(val, "text"))
                    self.execute([item for item in val if item[0] != "text"])
                else:
                    self.tooltips.append(val)
            elif key == "set_variable":
                self.vars[field(val, "name")] = self.num(field(val, "value"))
            elif key == "change_variable":
                name = field(val, "name")
                n = self.vars.get(name, 0)
                for op, _, arg in ((k, o, v) for k, o, v in val if k != "name"):
                    x = self.num(arg)
                    n = {"add": n + x, "subtract": n - x, "multiply": n * x,
                         "divide": n / x if x else n}[op]
                self.vars[name] = n
            elif key == "remove_variable":
                self.vars.pop(val, None)
            elif key == "set_global_variable":
                self.globals.add(field(val, "name"))
                try:
                    self.global_values[field(val, "name")] = self.num(field(val, "value"))
                except ValueError:
                    pass  # value = yes: a flag
            elif key == "change_global_variable":
                name = field(val, "name")
                self.global_values[name] = self.global_values.get(name, 0) + self.num(field(val, "add"))
            elif key == "save_scope_as":
                self.scopes[val] = "ROOT"  # every save modelled here is of the event's own country
            elif key == "trigger_event":
                self.events.append({k: v for k, _, v in val})
            elif key == "random_list":
                if not self.picks:
                    raise AssertionError("a random_list ran with no pick given")
                entry = [body for _, _, body in val][self.picks.pop(0)]
                self.execute([item for item in entry if item[0] != "modifier"])
            elif key == "debug_log":
                self.logs.append(val)
            elif key in INERT_EFFECTS:
                continue
            elif key in self.overrides:
                self.ran.append(key)
                if self.overrides[key] is not None:
                    self.execute(copy.deepcopy(self.overrides[key]))
            elif key in REGISTRY:
                if key in EFFECTS or REGISTRY.writes_cycle(key):
                    params = {k: v for k, _, v in val} if isinstance(val, list) else {}
                    self.execute(substitute(copy.deepcopy(REGISTRY.body(key)), params))
                # else: an effect that never writes the cycle; nothing to model
            else:
                raise AssertionError(f"unmodelled effect {key}")


def run(effect, variables, laws=(), scopes=(), **params):
    it = Interp(variables, laws, scopes)
    it.execute(substitute(copy.deepcopy(EFFECTS[effect]), params))
    return it


def option_bodies(event_id):
    options = []
    for key, _, val in MINOR_EVENTS[event_id]:
        if key == "option":
            options.append((field(val, "name"), [i for i in val if i[0] not in OPTION_META]))
    return options


def run_option(body, variables, laws=(), scopes=()):
    it = Interp(variables, laws, scopes)
    it.execute(copy.deepcopy(body))
    return it


VALUES = (0, 2, 5, 6.5, 12, 25, 40, 55, 90, 100)
MOMENTA = (-8, -5.5, -5, -3.5, -1, 0, 2, 5)


def raises(body, **extra):
    """The grid states in which running ``body`` leaves a cycle figure higher."""
    bad = []
    for value, momentum in itertools.product(VALUES, MOMENTA):
        start = {"finance_cycle_value": value, "finance_cycle_momentum": momentum,
                 "bubble_pressure": 30, **extra}
        end = run_option(body, start).vars
        if (end["finance_cycle_value"] > value + EPS
                or end["finance_cycle_momentum"] > momentum + EPS):
            bad.append((value, momentum, end["finance_cycle_value"], end["finance_cycle_momentum"]))
    return bad


class CheckerBitesTest(unittest.TestCase):
    def test_the_old_reset_is_caught(self):
        # The pre-fix behaviour for a Market Correction: set to 40 and -1.
        old = [("set_variable", "=", [("name", "=", "finance_cycle_value"), ("value", "=", "40")]),
               ("set_variable", "=", [("name", "=", "finance_cycle_momentum"), ("value", "=", "-1")])]
        self.assertTrue(raises(old))

    def test_an_unbracketed_softening_add_is_caught(self):
        old = [("change_variable", "=", [("name", "=", "finance_cycle_value"), ("add", "=", "5")])]
        self.assertTrue(raises(old))


class OriginCrashTest(unittest.TestCase):
    SEVERITIES = (0, 15, 19.9, 20, 39, 40, 59, 60, 79, 80, 100)

    def test_never_raises_either_figure(self):
        for severity in self.SEVERITIES:
            with self.subTest(severity=severity):
                body = [("apply_banking_crash_origin_effects", "=", "yes")]
                self.assertEqual(raises(body, crash_severity=severity), [])

    def test_still_resets_a_healthy_cycle_to_the_tier(self):
        # The ceiling is not a no-op: a boom is brought down to the tier figure.
        for severity, value, momentum in ((85, 5, -5), (65, 10, -4), (45, 20, -3),
                                          (25, 30, -2), (5, 40, -1)):
            with self.subTest(severity=severity):
                end = run("apply_banking_crash_origin_effects",
                          {"finance_cycle_value": 90, "finance_cycle_momentum": 3,
                           "bubble_pressure": 70, "crash_severity": severity}).vars
                self.assertEqual((end["finance_cycle_value"], end["finance_cycle_momentum"],
                                  end["bubble_pressure"]), (value, momentum, 0))

    def test_a_country_already_below_the_tier_keeps_what_it_has(self):
        # The reported case: a Market Correction (40, -1) reaching a Downturn.
        end = run("apply_banking_crash_origin_effects",
                  {"finance_cycle_value": 12, "finance_cycle_momentum": -3.5,
                   "bubble_pressure": 4, "crash_severity": 10}).vars
        self.assertEqual((end["finance_cycle_value"], end["finance_cycle_momentum"]), (12, -3.5))
        self.assertEqual(end["bubble_pressure"], 0)  # the bubble is still cleared


class SofteningTest(unittest.TestCase):
    def test_a_response_softens_but_cannot_lift_above_the_pre_crash_level(self):
        # Deposit guarantee: +10 value, +2 momentum on a systemic crash.
        args = dict(TT_KEY="X", CYCLE_ADD=10, MOMENTUM_ADD=2, COST_SCALE="x",
                    INTERVENTION="x", RADICALS="small")
        healthy = run("apply_banking_crash_softening_option_effect",
                      {"finance_cycle_value": 90, "finance_cycle_momentum": 3, "crash_severity": 85},
                      **args).vars
        # origin 5 / -5, then the response: 15 / -3. Softened, and nothing held back.
        self.assertEqual((healthy["finance_cycle_value"], healthy["finance_cycle_momentum"]), (15, -3))
        shallow = run("apply_banking_crash_softening_option_effect",
                      {"finance_cycle_value": 12, "finance_cycle_momentum": -3.5, "crash_severity": 85},
                      **args).vars
        # the response could reach 15 / -3, which is above where it stood: held at 12 / -3.5.
        self.assertEqual((shallow["finance_cycle_value"], shallow["finance_cycle_momentum"]), (12, -3.5))

    def test_the_bracket_leaves_nothing_behind(self):
        end = run("apply_banking_crash_softening_option_effect",
                  {"finance_cycle_value": 50, "finance_cycle_momentum": 0, "crash_severity": 45},
                  TT_KEY="X", CYCLE_ADD=3, MOMENTUM_ADD=1, COST_SCALE="x",
                  INTERVENTION="x", RADICALS="small").vars
        for name in PRIOR_VARS:
            self.assertNotIn(name, end)

    def test_hold_without_a_recorded_state_changes_nothing(self):
        # An unrecorded var: reads 0 in the engine, which would drag the cycle to 0.
        end = run("banking_crash_hold_to_prior_state",
                  {"finance_cycle_value": 40, "finance_cycle_momentum": 1}).vars
        self.assertEqual((end["finance_cycle_value"], end["finance_cycle_momentum"]), (40, 1))


class ContagionScareTest(unittest.TestCase):
    LAWS = ((), ("law_command_economy",), ("law_cooperative_ownership",))

    def scare(self, value, momentum, laws=()):
        end = run("apply_banking_contagion_effects",
                  {"finance_cycle_value": value, "finance_cycle_momentum": momentum,
                   "contagion_crash": 0}, laws).vars
        return end["finance_cycle_value"], end["finance_cycle_momentum"]

    def test_a_scare_still_lowers_a_healthy_cycle(self):
        self.assertEqual(self.scare(50, 0), (47, -1))
        self.assertEqual(self.scare(50, 0, ("law_command_economy",)), (49, -0.5))
        self.assertEqual(self.scare(50, 0, ("law_cooperative_ownership",)), (48, -0.5))

    def test_the_floor_clamps_never_lift_a_country_under_them(self):
        self.assertEqual(self.scare(7, 0), (5, -1))        # clamped, still lower than 7
        self.assertEqual(self.scare(2, 0), (2, -1))        # was 5 before the fix
        self.assertEqual(self.scare(50, -7), (47, -7))     # was -5 before the fix
        self.assertEqual(self.scare(50, -4.5), (47, -5))   # clamped, still lower than -4.5


class EveryCrashOptionTest(unittest.TestCase):
    """Every option of the origin and contagion events, over the grid."""

    def test_origin_event_options(self):
        options = option_bodies("minor_events_timelineextended.6")
        self.assertGreaterEqual(len(options), 12)
        for name, body in options:
            for severity in (5, 25, 45, 65, 85):
                with self.subTest(option=name, severity=severity):
                    self.assertEqual(raises(body, crash_severity=severity), [])
                    it = run_option(body, {"finance_cycle_value": 50, "finance_cycle_momentum": 0,
                                           "bubble_pressure": 30, "crash_severity": severity})
                    for prior in PRIOR_VARS:
                        self.assertNotIn(prior, it.vars)
                    self.assertIn("CRASH_NO_RAISE_DESC", it.tooltips)

    def test_contagion_event_options(self):
        options = option_bodies("minor_events_timelineextended.7")
        self.assertGreaterEqual(len(options), 5)
        for name, body in options:
            # event .7 keeps its roll as a saved scope (its immediate): the country, if it crashed. A
            # scare saves nothing, and may hold the upstream country's (ContagionRollScopeTest).
            rolls = ((0, {}), (0, ContagionRollScopeTest.INHERITED), (1, ContagionRollScopeTest.OWN))
            for (crashed, scopes), laws in itertools.product(rolls, ContagionScareTest.LAWS):
                for severity in (5, 45, 85):
                    with self.subTest(option=name, contagion_crash=crashed, scopes=scopes, laws=laws,
                                      sev=severity):
                        for value, momentum in itertools.product(VALUES, MOMENTA):
                            start = {"finance_cycle_value": value, "finance_cycle_momentum": momentum,
                                     "bubble_pressure": 30, "contagion_crash": crashed,
                                     "crash_severity": severity}
                            it = run_option(body, start, laws, scopes)
                            self.assertLessEqual(it.vars["finance_cycle_value"], value + EPS)
                            self.assertLessEqual(it.vars["finance_cycle_momentum"], momentum + EPS)
                            for prior in PRIOR_VARS:
                                self.assertNotIn(prior, it.vars)


class ContagionRollScopeTest(unittest.TestCase):
    """Event .7 keeps its roll in a saved scope and reads it as this country's own.

    A saved scope rides into the events an `after` triggers, so a country a cascade
    reaches arrives holding the upstream country as contagion_crashed, and
    clear_saved_scope did not remove it. On 2026-10-16 the European Union rolled a
    scare (its save: banking_crisis_wave_scared) and still took the crash branch, at
    the tier of a crash_severity an earlier crash had left (25: cycle 59.9 to 30), and
    the cascade (banking_crisis_wave_counted). Every read now asks that the saved
    country be ROOT (banking_contagion_own_roll_crashed).
    """
    EVENT = "minor_events_timelineextended.7"
    INHERITED = {"contagion_crashed": "UPSTREAM"}
    OWN = {"contagion_crashed": "ROOT"}
    EU = {"finance_cycle_value": 59.871, "finance_cycle_momentum": 0.012,
          "bubble_pressure": 0, "contagion_crash": 0, "crash_severity": 25.083}
    COOP = ("law_cooperative_ownership",)

    def block(self, name):
        return field(MINOR_EVENTS[self.EVENT], name)

    def cascade(self):
        """The `if` in `after` that spreads the contagion on."""
        return next(val for key, _, val in self.block("after")
                    if key == "if" and "banking_cycle_spread_contagion" in repr(val))

    def test_the_eu_case_an_inherited_roll_plays_as_a_scare(self):
        for name, body in option_bodies(self.EVENT):
            with self.subTest(option=name):
                end = run_option(body, self.EU, self.COOP, self.INHERITED).vars
                # the cooperative scare: -2 value, -0.5 momentum
                self.assertAlmostEqual(end["finance_cycle_value"], 57.871)
                self.assertAlmostEqual(end["finance_cycle_momentum"], -0.488)

    def test_its_own_crash_still_crashes(self):
        start = dict(self.EU, contagion_crash=1)
        for name, body in option_bodies(self.EVENT):
            with self.subTest(option=name):
                end = run_option(body, start, self.COOP, self.OWN).vars
                # severity 25: the Market Downturn's ceilings
                self.assertEqual((end["finance_cycle_value"], end["finance_cycle_momentum"]), (30, -2))

    def test_after_cascades_on_its_own_roll_only(self):
        limit = field(self.cascade(), "limit")
        self.assertTrue(Interp({}, scopes=self.OWN).check(limit))
        self.assertFalse(Interp({}, scopes=self.INHERITED).check(limit))
        self.assertFalse(Interp({}).check(limit))

    def test_nothing_reads_the_roll_by_existence_alone(self):
        needle = repr(("exists", "=", "scope:contagion_crashed"))
        for key, _, val in MINOR_EVENTS[self.EVENT]:
            if key in ("option", "after"):
                self.assertNotIn(needle, repr(val), key)
        self.assertNotIn(needle, repr(EFFECTS["apply_banking_contagion_effects"]))

    def test_crash_only_options_ask_for_its_own_roll(self):
        gated = [field(val, "name") for key, _, val in MINOR_EVENTS[self.EVENT]
                 if key == "option" and any(k == "trigger" for k, _, _ in val)
                 and ("banking_contagion_own_roll_crashed", "=", "yes") in field(val, "trigger")]
        self.assertEqual(len(gated), 3)  # capital controls, monetary intervention, confidence messaging

    def test_immediate_saves_the_roll_after_rolling_it(self):
        text = repr(self.block("immediate"))
        self.assertLess(text.index("banking_contagion_crash_check"), text.index("save_scope_as"))
        self.assertNotIn("clear_saved_scope", text)  # it did not remove an inherited scope

    def test_the_cascade_and_options_do_not_read_the_variable(self):
        # Two copies of the event can be open for one country at once; only the self-check reads it.
        self.assertNotIn("var:contagion_crash", repr(self.cascade()))
        for key, _, val in MINOR_EVENTS[self.EVENT]:
            if key == "option":
                self.assertNotIn("var:contagion_crash", repr(val))

    def test_the_text_reads_its_own_roll(self):
        # A second copy's roll overwrites contagion_crash, so the text would read the other copy's outcome.
        for part in ("title", "desc", "flavor"):
            with self.subTest(part=part):
                block = self.block(part)
                self.assertNotIn("var:contagion_crash", repr(block))
                self.assertNotIn("'contagion_crash'", repr(block))
                descs = field(block, "first_valid")
                cascade = [field(val, "trigger") for _, _, val in descs
                           if "_cascade" in field(val, "desc")]
                self.assertTrue(cascade)
                for trigger in cascade:
                    own = trigger[:1]
                    self.assertEqual(own, [("banking_contagion_own_roll_crashed", "=", "yes")])
                    self.assertTrue(Interp({}, scopes=self.OWN).check(own))
                    # queued, or a scare: no saved scope yet, or the upstream country's
                    self.assertFalse(Interp({"contagion_crash": 1}, scopes=self.INHERITED).check(own))
                    self.assertFalse(Interp({"contagion_crash": 1}).check(own))


class ContagionSelfCheckTest(unittest.TestCase):
    """TE_SELF_CHECK contagion_roll_scope judges a copy of event .7 only when it was alone.

    Two copies used to be open for one country at once (a second origin crashing in the same pulse
    clears the reached marks), and contagion_crash is the country's, so the later copy's roll
    overwrote the earlier one's. The check compared each copy's own saved scope with it, and
    logged five BROKEN lines in the 2026-10-17 observer run, both directions, with every copy's
    options following its own roll. It counts the copies open and judges a copy only when the
    count is 1 at its `after` and the variable is still set. Since the block (ContagionBlockTest)
    a second copy should never open; when one does, contagion_one_open's BROKEN reports it, once
    a game, and the roll goes unjudged. These run the two effects on their own, opening copies
    directly, so they reach the interleavings the block now rules out.
    """
    EVENT = "minor_events_timelineextended.7"

    def setUp(self):
        self.vars, self.globals, self.logs = {}, set(), []

    def _run(self, effect, scopes):
        it = Interp(self.vars, scopes=scopes, global_vars=self.globals)
        it.execute(copy.deepcopy(EFFECTS[effect]))
        self.vars, self.globals = it.vars, it.globals
        self.logs += it.logs

    def open(self, crashed, inherited=False, saved="ROOT"):
        """A copy's immediate: the count, then its roll and its save. Returns the copy's own saved scopes.

        ``saved`` is what the copy's crash leaves in contagion_crashed: ROOT when the save replaced an
        inherited scope, UPSTREAM when it did not (a genuine failure the check must still catch).
        """
        scopes = {"contagion_crashed": "UPSTREAM"} if inherited else {}
        self._run("banking_contagion_selfcheck_open", scopes)
        self.vars["contagion_crash"] = 1 if crashed else 0
        if crashed:
            scopes["contagion_crashed"] = saved
        return scopes

    def close(self, scopes):
        """A copy's after: the verdict and count, then the remove_variable every `after` runs."""
        self._run("banking_contagion_selfcheck_close", scopes)
        self.vars.pop("contagion_crash", None)

    def lines(self, word, check="contagion_roll_scope"):
        return [line for line in self.logs if line.startswith(f"TE_SELF_CHECK {word} {check}")]

    def test_a_copy_alone_whose_roll_agrees_logs_nothing_bad(self):
        for crashed, inherited in itertools.product((0, 1), repeat=2):
            with self.subTest(crashed=crashed, inherited=inherited):
                self.setUp()
                self.close(self.open(crashed, inherited))
                self.assertEqual(self.lines("BROKEN") + self.lines("BROKEN", "contagion_one_open"), [])
                self.assertEqual(len(self.lines("OK")), int(crashed and inherited))
                self.assertNotIn("banking_contagion_open", self.vars)
                self.assertNotIn("banking_contagion_roll_inherited", self.vars)

    def test_ok_is_once_a_game(self):
        for _ in range(3):
            self.close(self.open(1, inherited=True))
        self.assertEqual(len(self.lines("OK")), 1)

    def test_a_copy_alone_still_catches_a_save_that_did_not_replace(self):
        self.close(self.open(1, inherited=True, saved="UPSTREAM"))
        self.assertEqual(len(self.lines("BROKEN")), 1)
        self.assertIn("roll=crash read=scare", self.lines("BROKEN")[0])
        self.assertEqual(self.lines("OK"), [])

    def test_a_copy_alone_still_catches_a_scare_read_as_a_crash(self):
        scopes = self.open(0)
        scopes["contagion_crashed"] = "ROOT"  # an inherited scope naming this country
        self.close(scopes)
        self.assertEqual(len(self.lines("BROKEN")), 1)
        self.assertIn("roll=scare read=crash", self.lines("BROKEN")[0])

    def test_the_observer_runs_pairs_now_break_the_block_and_judge_no_roll(self):
        # SIC, GBR, SAR, PAP: a copy that crashed closes after a second copy rolled a scare.
        a = self.open(1)
        b = self.open(0)
        self.close(a)
        self.close(b)
        # NOR: the mirror, a scare closing after a second copy crashed.
        c = self.open(0, inherited=True)
        d = self.open(1, inherited=True)
        self.close(c)
        self.close(d)
        self.assertEqual(self.lines("BROKEN") + self.lines("OK") + self.lines("NO_VERDICT"), [])
        broken = self.lines("BROKEN", "contagion_one_open")
        self.assertEqual(len(broken), 1)  # once a game, from the first pair
        self.assertIn("open=", broken[0])
        self.assertIn("turned_away=", broken[0])
        self.assertNotIn("banking_contagion_open", self.vars)

    def test_no_interleaving_of_three_copies_is_judged_on_another_copys_roll(self):
        # Every order of three copies' immediates and afters (each opens before it closes), every roll
        # and every inheritance: the save always replaces, so a BROKEN or an OK would be a false verdict
        # unless it came from a copy whose own roll matched the variable. Never BROKEN; OK only when
        # a copy was alone and its own crash was inherited. The block's BROKEN comes once, exactly
        # when some copy opened while another was open.
        def orders(opened, done):
            if len(done) == 3:
                yield []
                return
            for i in range(3):
                if i not in opened:
                    for rest in orders(opened | {i}, done):
                        yield [("open", i), *rest]
                elif i not in done:
                    for rest in orders(opened, done | {i}):
                        yield [("close", i), *rest]
        sequences = list(orders(frozenset(), frozenset()))
        self.assertEqual(len(sequences), 90)

        def overlaps(seq):
            live = 0
            for step, _ in seq:
                live += 1 if step == "open" else -1
                if live > 1:
                    return True
            return False
        self.assertEqual(sum(not overlaps(seq) for seq in sequences), 6)  # one copy at a time, 3! orders
        for rolls in itertools.product((0, 1), repeat=3):
            for inherited in itertools.product((False, True), repeat=3):
                for seq in sequences:
                    self.setUp()
                    scopes = {}
                    for step, i in seq:
                        if step == "open":
                            scopes[i] = self.open(rolls[i], inherited[i])
                        else:
                            self.close(scopes[i])
                    with self.subTest(rolls=rolls, inherited=inherited, seq=seq):
                        self.assertEqual(self.lines("BROKEN"), [])
                        self.assertLessEqual(len(self.lines("OK")), 1)
                        self.assertNotIn("banking_contagion_open", self.vars)
                        self.assertEqual(len(self.lines("BROKEN", "contagion_one_open")), int(overlaps(seq)))
                        self.assertEqual(self.lines("OK", "contagion_one_open"), [])  # nothing turned away
                        if seq[:2] == [("open", 0), ("close", 0)] and rolls[0] and inherited[0]:
                            # copy 0 was alone, inherited a scope and crashed: the case OK is for
                            self.assertEqual(len(self.lines("OK")), 1)

    def test_a_copy_that_never_closes_suppresses_verdicts_but_fakes_none(self):
        # Opened directly, past the spread: the count stays high, so no roll is judged again and the
        # block reports a second copy open. In play the spread sends no copy while the lost one's mark
        # lasts, and the next one it sends clears the leftovers (ContagionBlockTest, the lost copy).
        self.open(1)  # its country annexed before its after ran
        self.close(self.open(1, inherited=True, saved="UPSTREAM"))
        self.close(self.open(1, inherited=True))
        self.assertEqual(self.lines("BROKEN") + self.lines("OK"), [])
        self.assertEqual(len(self.lines("BROKEN", "contagion_one_open")), 1)

    def test_the_event_counts_before_its_roll_and_judges_before_its_cascade(self):
        event = MINOR_EVENTS[self.EVENT]
        body = field(event, "immediate")
        immediate = [key for key, _, _ in body]
        # the roll is only a fallback here now (the hidden event .9 made it), so it sits in an `if`
        roll = next(i for i, (key, _, val) in enumerate(body)
                    if key == "if" and "banking_contagion_crash_check" in repr(val))
        self.assertLess(immediate.index("banking_contagion_selfcheck_open"), roll)
        after = field(event, "after")
        keys = [key for key, _, _ in after]
        self.assertEqual(keys[0], "banking_contagion_selfcheck_close")
        # at the top level of `after`, after the cascade: the check reads a missing value as "a copy
        # closed"; guarded only because banking_contagion_clear_stale may have removed it already
        removal = [("if", "=", [("limit", "=", [("has_variable", "=", "contagion_crash")]),
                                ("remove_variable", "=", "contagion_crash")])]
        self.assertEqual(after[-2:-1], removal)
        self.assertNotIn("debug_log", repr(after))


class ContagionScareOnlyTest(unittest.TestCase):
    """Scare only for a year (owner, 2026-10-17): a country that crashed, at home or by contagion,
    takes only a scare from contagion for the next year.

    A crash zeroes bubble pressure, but banking_contagion_crash_check still weighs a crash at 5 to
    30 points of the origin's severity against 100 for a scare. Every crash now sets
    banking_crashed_last_year (365 days) where it is decided, and while it is set the contagion roll
    is skipped. These run the real roll, with the random_list entries picked and the script values
    pinned.
    """
    EVENT = "minor_events_timelineextended.7"
    VALUES = {"banking_crash_severity_scale_value": 0.55, "banking_contagion_severity_economy_mult": 1,
              "banking_crash_severity_economy_mult": 1, "this_country_gdp_value": 1}
    ORIGIN = {"banking_crash_origin_country": {"crash_severity": 50}}
    PINNED = {"te_mon_has_effective_backstop": False}
    # The history chart's marker and the demographic wealth shock: neither touches the roll.
    ASIDE = {"te_history_record_banking_marker": None, "te_demog_wc_shock": None}

    def run_effect(self, body, variables, picks, overrides=None):
        it = Interp(variables, values=self.VALUES, picks=list(picks), others=self.ORIGIN,
                    trigger_values=self.PINNED, overrides={**self.ASIDE, **(overrides or {})})
        it.execute(copy.deepcopy(body))
        return it

    def test_a_country_that_crashed_within_the_year_only_takes_a_scare(self):
        for bubble, picks in itertools.product((0, 40, 100), ([0, 2], [1])):
            with self.subTest(bubble=bubble, picks=picks):
                it = self.run_effect(EFFECTS["banking_contagion_crash_check"],
                                     {"bubble_pressure": bubble, "banking_crashed_last_year": 1}, picks)
                self.assertEqual(it.vars["contagion_crash"], 0)
                self.assertIn("banking_crisis_wave_scared", it.vars)  # a survivor, for the Great Depression
                for name in ("banking_crisis_wave_crashed", "crash_severity", "banking_recent_crash"):
                    self.assertNotIn(name, it.vars)
                self.assertEqual(it.picks, picks)  # no roll was made

    def test_without_the_gate_a_recent_crash_crashes_again(self):
        # The mutation: the roll without its scare-only branch. The marker is then ignored, and the
        # crash entry crashes a country whose bubble its last crash zeroed.
        check = EFFECTS["banking_contagion_crash_check"]
        gate = check[0]
        self.assertEqual(field(gate[2], "limit"), [("banking_contagion_scare_only", "=", "yes")])
        ungated = field(check, "else") + check[2:]
        it = self.run_effect(ungated, {"bubble_pressure": 0, "banking_crashed_last_year": 1}, [0, 2])
        self.assertEqual(it.vars["contagion_crash"], 1)
        self.assertIn("banking_crisis_wave_crashed", it.vars)

    def test_past_the_year_the_roll_decides(self):
        crash = self.run_effect(EFFECTS["banking_contagion_crash_check"], {"bubble_pressure": 40}, [0, 2])
        self.assertEqual(crash.vars["contagion_crash"], 1)
        self.assertIn("banking_crisis_wave_crashed", crash.vars)
        self.assertAlmostEqual(crash.vars["crash_severity"], 40 * 0.55 + 10)  # an origin at 50: +10
        self.assertIn("banking_recent_crash", crash.vars)
        self.assertIn("banking_crashed_last_year", crash.vars)  # and its own year starts
        self.assertEqual(crash.picks, [])
        scare = self.run_effect(EFFECTS["banking_contagion_crash_check"], {"bubble_pressure": 40}, [1])
        self.assertEqual(scare.vars["contagion_crash"], 0)
        self.assertIn("banking_crisis_wave_scared", scare.vars)
        self.assertNotIn("banking_crashed_last_year", scare.vars)  # a scare starts no year

    def test_an_origin_crash_starts_the_year(self):
        stubs = {"banking_crisis_wave_init": None, "banking_cycle_spread_contagion": None}
        body = EFFECTS["banking_cycle_check_and_execute_crash"]
        crash = self.run_effect(body, {"bubble_pressure": 60, "finance_cycle_value": 80}, [0, 2], overrides=stubs)
        self.assertEqual(crash.vars["crash"], 1)
        self.assertIn("banking_crashed_last_year", crash.vars)
        self.assertIn("banking_recent_crash", crash.vars)
        self.assertEqual([name for name in crash.ran if name in stubs],
                         ["banking_crisis_wave_init", "banking_cycle_spread_contagion"])
        calm = self.run_effect(body, {"bubble_pressure": 60, "finance_cycle_value": 80}, [1], overrides=stubs)
        self.assertNotIn("banking_crashed_last_year", calm.vars)

    def test_the_year_is_a_year_and_set_where_each_crash_is_decided(self):
        mark = field(EFFECTS["banking_mark_crashed_last_year"], "set_variable")
        self.assertEqual((field(mark, "name"), field(mark, "days")), ("banking_crashed_last_year", "365"))

        def calls(body):
            for key, _, val in body:
                if key == "banking_mark_crashed_last_year":
                    yield body
                elif isinstance(val, list):
                    yield from calls(val)
        for name in ("banking_contagion_crash_check", "banking_cycle_check_and_execute_crash"):
            with self.subTest(effect=name):
                sites = list(calls(EFFECTS[name]))
                self.assertEqual(len(sites), 1)
                self.assertIn("banking_recent_crash", repr(sites[0]))  # the branch that decided a crash
        # not where the bubble is zeroed: that runs in the options, months later, and in their tooltips
        self.assertNotIn("banking_crashed_last_year", repr(EFFECTS["apply_banking_crash_origin_effects"]))
        self.assertNotIn("banking_mark_crashed_last_year", repr(EFFECTS["apply_banking_crash_origin_effects"]))

    def test_the_event_plays_a_forced_scare_as_a_scare(self):
        event = MINOR_EVENTS[self.EVENT]
        it = self.run_effect(field(event, "immediate"), {"bubble_pressure": 90, "banking_crashed_last_year": 1}, [])
        self.assertEqual(it.vars["contagion_crash"], 0)
        self.assertNotIn("contagion_crashed", it.scopes)
        own = [("banking_contagion_own_roll_crashed", "=", "yes")]
        self.assertFalse(Interp(it.vars, scopes=it.scopes).check(own))
        # The crash text and the crash-only options all ask for its own crash
        # (ContagionRollScopeTest); the two ungated options are the scare's.
        ungated = [field(val, "name") for key, _, val in event
                   if key == "option" and not any(k == "trigger" for k, _, _ in val)]
        self.assertEqual(ungated, [f"{self.EVENT}.a", f"{self.EVENT}.b"])
        for name, body in option_bodies(self.EVENT)[:2]:
            with self.subTest(option=name):
                end = run_option(body, {"finance_cycle_value": 50, "finance_cycle_momentum": 0,
                                        "bubble_pressure": 90, "contagion_crash": 0}, (), it.scopes).vars
                self.assertEqual((end["finance_cycle_value"], end["finance_cycle_momentum"]), (47, -1))
                self.assertEqual(end["bubble_pressure"], 90)  # a scare leaves the bubble


# Event .7's roll, for the block's tests: banking_contagion_crash_check is a random_list over script
# values, so it is replaced by its outcome, with the wave marks it sets (ContagionBlockTest checks the
# real effect sets the same two marks).
CRASH_ROLL = parse_body("""
set_variable = { name = contagion_crash value = $ROLL$ }
if = {
    limit = { var:contagion_crash > 0 }
    set_variable = { name = banking_crisis_wave_crashed value = 1 }
    set_variable = { name = crash_severity value = $SEVERITY$ }
}
else = {
    set_variable = { name = banking_crisis_wave_scared value = 1 }
}
""")


class Country:
    """One country a contagion wave keeps reaching: the real reach, wave init, the hidden roll event,
    the popup's immediate and after.

    Run by Interp with only the roll (CRASH_ROLL) and the after's cascade internals (its own spread,
    the Great Depression check, the post-event refresh) replaced; ``mutations`` replaces more, for
    the tests that show the checks bite. A wave usually starts elsewhere (``new_wave``); in
    ``become_origin`` the country's own crash starts one. The hidden event's week and the popup's day
    are one step here (``fire``): nothing else in the model happens between them.
    """
    EVENT = "minor_events_timelineextended.7"
    DECIDER = "minor_events_timelineextended.9"
    COOLDOWN = "banking_contagion_scare_cooldown"
    STUBS = {"banking_cycle_spread_contagion": None,
             "banking_crisis_wave_check_great_depression": None,
             "banking_cycle_post_event_refresh": None}

    def __init__(self, mutations=None, immediate=None, after=None, init=None):
        self.vars, self.globals, self.gvals, self.logs = {}, set(), {}, []
        self.init = init if init is not None else EFFECTS["banking_crisis_wave_init"]
        self.origin = False       # the wave now running is this country's own crash
        self.queued, self.open = [], []  # the copies of the event, each its saved scopes
        self.overrides = {**self.STUBS, **(mutations or {})}
        self.decider = field(MINOR_EVENTS[self.DECIDER], "immediate")
        self.immediate = immediate if immediate is not None else field(MINOR_EVENTS[self.EVENT], "immediate")
        self.after = after if after is not None else field(MINOR_EVENTS[self.EVENT], "after")
        self.sent = self.rolls = self.cascades = 0
        self.silent = 0           # copies the hidden event ended without a popup
        self.broken = []          # cooldown rules a fire broke, in words
        self.turned_away = 0      # reaches turned away since the copy now held was sent
        self.lost = False         # a copy was lost since the last one was sent: its leftovers wait
        self.owed_ok = False      # a copy closed alone with a reach turned away for it
        self.severities = []      # crash_severity as each copy's options read it

    def run(self, body, scopes=None, extra=None):
        it = Interp(self.vars, scopes=scopes or {}, global_vars=self.globals,
                    overrides={**self.overrides, **(extra or {})},
                    values={"this_country_gdp_value": 1}, global_values=self.gvals)
        it.execute(copy.deepcopy(body))
        self.vars, self.globals, self.gvals = it.vars, it.globals, it.global_values
        self.logs += it.logs
        return it

    def reached(self):
        return Interp(self.vars).check([("banking_crisis_wave_reached", "=", "yes")])

    def new_wave(self):
        """An origin crashes elsewhere: banking_crisis_wave_init as it reaches this country."""
        body = [("if", "=", field(self.init, "every_country"))]  # its limit, then the removals
        body += [item for item in self.init if item[0] == "set_global_variable"]
        self.run(body)
        self.origin = False

    def become_origin(self):
        """This country's own crash starts a wave: all of banking_crisis_wave_init, run here (its
        every_country clears this country's marks too, then it marks itself)."""
        body = [("if", "=", val) if key == "every_country" else (key, op, val) for key, op, val in self.init]
        self.run(body)
        self.origin = True

    def spread(self):
        """A spread whose roll for this country came up: the wave test of its every_country limit
        (structural test below), then banking_contagion_reach."""
        if self.reached():
            return "passed by"
        it = self.run([("banking_contagion_reach", "=", "yes")])
        for event in it.events:
            assert event["id"] == self.DECIDER and event.get("days"), event
            self.queued.append({})
            self.sent += 1
            self.turned_away = 0
            self.lost = False
        if not it.events:
            self.turned_away += 1
        return {0: "turned away", 1: "sent"}.get(len(it.events), "sent twice")

    def fire(self, crashed):
        """A queued copy's week is up. The hidden event rolls and either ends, or sends the popup,
        which opens a day later. Returns "silent" or "popup"; breaks of the cooldown rule are kept in
        ``broken`` (a crash always shows, a scare shows once in two years and starts the cooldown)."""
        scopes = self.queued.pop(0)
        cooling = self.COOLDOWN in self.vars
        roll = substitute(copy.deepcopy(CRASH_ROLL), {"ROLL": int(crashed), "SEVERITY": 40 + self.sent})
        decided = self.run(self.decider, scopes, {"banking_contagion_crash_check": roll})
        self.rolls += decided.ran.count("banking_contagion_crash_check")
        shown = bool(decided.events)
        if shown:
            assert [(e["id"], e.get("days")) for e in decided.events] == [(self.EVENT, "1")], decided.events
        if bool(crashed) and not shown:
            self.broken.append("a crash was kept from its popup")
        if not crashed and shown and cooling:
            self.broken.append("a scare was shown inside the cooldown")
        if not crashed and not shown and not cooling:
            self.broken.append("a scare was held back with no cooldown running")
        if not crashed and shown and not cooling and self.COOLDOWN not in self.vars:
            self.broken.append("a shown scare did not start the cooldown")
        if crashed and shown and cooling != (self.COOLDOWN in self.vars):
            self.broken.append("a crash changed the cooldown")
        if not shown:
            self.silent += 1
            self.turned_away = 0
            return "silent"
        it = self.run(self.immediate, decided.scopes)
        self.rolls += it.ran.count("banking_contagion_crash_check")
        self.open.append({"scopes": it.scopes, "severity": 40 + self.sent if crashed else None})
        return "popup"

    def fire_legacy(self, crashed):
        """A popup an older build sent straight to .7, with no hidden event before it: it has not
        rolled, so its own immediate does."""
        scopes = self.queued.pop(0)
        roll = substitute(copy.deepcopy(CRASH_ROLL), {"ROLL": int(crashed), "SEVERITY": 40 + self.sent})
        it = self.run(self.immediate, scopes, {"banking_contagion_crash_check": roll})
        self.rolls += it.ran.count("banking_contagion_crash_check")
        self.open.append({"scopes": it.scopes, "severity": 40 + self.sent if crashed else None})

    def close(self):
        held = self.open.pop(0)
        if held["severity"] is not None:
            self.severities.append((held["severity"], self.vars.get("crash_severity")))
        alone = not self.open and not self.queued
        it = self.run(self.after, held["scopes"])
        self.cascades += it.ran.count("banking_cycle_spread_contagion")
        if alone and self.turned_away:
            self.owed_ok = True
        self.turned_away = 0

    def lose(self):
        """The open copy's `after` never runs (a revolution's winner holds the country's variables);
        the winner's banking entry removes the mark (je_banking_cycle's immediate)."""
        self.open.pop(0)
        self.vars.pop("banking_contagion_pending", None)
        self.lost = True

    def lines(self, word, check):
        return [line for line in self.logs if line.startswith(f"TE_SELF_CHECK {word} {check}")]

    def problems(self):
        """What is wrong now, in words; empty when the block holds."""
        found = []
        held = len(self.queued) + len(self.open)
        if held > 1:
            found.append("two contagion events at once")
        if ("banking_contagion_pending" in self.vars) != (held == 1):
            found.append("the mark is out of step with the event")
        decided = {"banking_crisis_wave_crashed", "banking_crisis_wave_scared"} & set(self.vars)
        if "banking_crisis_wave_hit" in self.vars and not decided and not self.queued:
            found.append("reached but undecided, with no roll to come (#428)")
        # The wave's count starts at 1, its origin; this country adds 1 when its own crash is counted,
        # unless it is that origin.
        counted = "banking_crisis_wave_counted" in self.vars and not self.origin
        if self.gvals.get("great_depression_wave_count", 1) != 1 + counted:
            found.append("the wave counted this country other than once for its crash")
        if self.rolls != self.sent - len(self.queued):
            found.append("a roll for a copy never sent")
        for own, read in self.severities:
            if own != read:
                found.append(f"options read crash_severity {read}, not their own {own}")
        if self.lines("BROKEN", "contagion_one_open") + self.lines("BROKEN", "contagion_roll_scope"):
            found.append("a BROKEN line")
        found.extend(self.broken)
        if len(self.lines("OK", "contagion_one_open")) != int(self.owed_ok):
            found.append("contagion_one_open OK without a turned-away reach, or missing after one")
        return found


class ContagionBlockTest(unittest.TestCase):
    """One contagion event per country at a time (owner, 2026-10-17: "Ideally, only one").

    banking_contagion_reach sets banking_contagion_pending when the spread sends event .7, the
    event's `immediate` sets it again and its `after` removes it, and a reach that finds it is
    turned away. A second origin crashing in the same pulse re-runs banking_crisis_wave_init,
    which clears every reached mark but not this one, so its spread no longer sends a second copy.
    """
    EVENT = "minor_events_timelineextended.7"
    LEFTOVERS = ("banking_contagion_pending", "banking_contagion_open", "banking_contagion_turned_away",
                 "banking_contagion_roll_inherited", "contagion_crash")

    def two_waves_in_one_pulse(self, country, crashed):
        country.new_wave()
        first = country.spread()
        country.new_wave()  # a second origin crashes in the same pulse
        second = country.spread()
        country.fire(crashed)
        country.close()
        return first, second

    def test_two_waves_in_one_pulse_open_one_event(self):
        for crashed in (0, 1):
            with self.subTest(crashed=crashed):
                c = Country()
                self.assertEqual(self.two_waves_in_one_pulse(c, crashed), ("sent", "turned away"))
                self.assertEqual((c.sent, c.rolls), (1, 1))  # one roll, one crash_severity
                self.assertEqual(c.problems(), [])
                self.assertEqual(len(c.lines("OK", "contagion_one_open")), 1)
                self.assertIn("turned_away=", c.lines("OK", "contagion_one_open")[0])
                # reached and decided in the wave now running, counted once, the cascade run once
                self.assertIn("banking_crisis_wave_hit", c.vars)
                self.assertIn("banking_crisis_wave_crashed" if crashed else "banking_crisis_wave_scared", c.vars)
                self.assertEqual(c.gvals["great_depression_wave_count"], 1 + crashed)
                self.assertEqual(c.cascades, crashed)
                for name in self.LEFTOVERS:
                    self.assertNotIn(name, c.vars)

    def test_a_wave_that_starts_while_the_event_is_open_takes_its_outcome(self):
        for crashed in (0, 1):
            with self.subTest(crashed=crashed):
                c = Country()
                c.new_wave()
                c.spread()
                c.fire(crashed)
                c.new_wave()
                self.assertEqual(c.spread(), "turned away")
                # the open event has rolled: its outcome goes on the new wave's books at once
                self.assertIn("banking_crisis_wave_hit", c.vars)
                self.assertIn("banking_crisis_wave_crashed" if crashed else "banking_crisis_wave_scared", c.vars)
                self.assertEqual(c.problems(), [])
                c.close()
                self.assertEqual(c.problems(), [])
                self.assertEqual(c.gvals["great_depression_wave_count"], 1 + crashed)

    def test_once_answered_the_country_can_be_reached_again(self):
        c = Country()
        c.new_wave()
        c.spread()
        c.fire(0)
        c.close()
        c.new_wave()
        self.assertEqual(c.spread(), "sent")
        self.assertEqual(c.problems(), [])
        self.assertEqual(c.lines("OK", "contagion_one_open"), [])  # nothing was turned away

    def test_a_lost_copy_frees_the_country_and_leaves_nothing_to_misread(self):
        # Its `after` never ran; once the mark is gone, the next copy sent clears the leftovers, so the
        # count is not taken for a second copy and its roll is judged on its own.
        c = Country()
        c.new_wave()
        c.spread()
        c.fire(1)
        c.lose()
        c.new_wave()
        self.assertEqual(c.spread(), "sent")
        c.fire(0)
        self.assertEqual(c.problems(), [])
        c.close()
        self.assertEqual(c.problems(), [])
        for name in self.LEFTOVERS:
            self.assertNotIn(name, c.vars)

    def test_a_copy_an_older_build_sent_is_marked_when_it_opens(self):
        c = Country()
        c.new_wave()
        c.vars["banking_crisis_wave_hit"] = 1
        c.queued.append({})  # sent before the block: no mark
        c.sent = 1
        c.fire_legacy(1)
        c.new_wave()
        self.assertEqual(c.spread(), "turned away")
        c.close()
        self.assertEqual(c.problems(), [])
        # and without the immediate's mark the second copy is sent
        immediate = [item for item in field(MINOR_EVENTS[self.EVENT], "immediate")
                     if item[0] != "banking_contagion_mark_pending"]
        c = Country(immediate=immediate)
        c.new_wave()
        c.queued.append({})
        c.sent = 1
        c.fire_legacy(1)
        c.new_wave()
        self.assertEqual(c.spread(), "sent")

    def test_an_origin_is_counted_once_in_its_own_wave(self):
        # The country's contagion event, from an earlier wave, has rolled a crash; before it is
        # answered, the country's own crash starts a wave. The wave's count of 1 is the country, so the
        # event's `after` must not count it again (banking_crisis_wave_init marks the origin counted).
        c = Country()
        c.new_wave()
        c.spread()
        c.fire(1)
        c.become_origin()
        self.assertEqual(c.gvals["great_depression_wave_count"], 1)
        c.close()
        self.assertEqual(c.gvals["great_depression_wave_count"], 1)
        self.assertEqual(c.problems(), [])
        # without the mark, the event's crash counted the origin twice
        init = [item for item in EFFECTS["banking_crisis_wave_init"]
                if item != ("set_variable", "=", [("name", "=", "banking_crisis_wave_counted"), ("value", "=", "1")])]
        self.assertEqual(len(init), len(EFFECTS["banking_crisis_wave_init"]) - 1)
        c = Country(init=init)
        c.new_wave()
        c.spread()
        c.fire(1)
        c.become_origin()
        c.close()
        self.assertEqual(c.gvals["great_depression_wave_count"], 2)
        self.assertIn("the wave counted this country other than once for its crash", c.problems())

    def explore(self, depth=6, **mutation):
        """Every sequence of up to ``depth`` steps from a first wave reaching the country: another
        wave reaching it, a wave starting elsewhere (init only), its own crash starting one, a later
        tier of the wave reaching it,
        the copy held firing (a crash or a scare), answering, or being lost, or the scare cooldown
        running out; then each copy still held
        fires and answers. Returns (sequences run, the problems found with their steps)."""
        actions = ("wave", "elsewhere", "origin", "tier", "crash", "scare", "close", "lose", "years")
        found, runs = [], 0

        def step(c, action):
            if action == "wave":
                c.new_wave()
                c.spread()
            elif action == "elsewhere":
                c.new_wave()
            elif action == "origin":
                c.become_origin()
            elif action == "tier":
                c.spread()
            elif action in ("crash", "scare"):
                c.fire(action == "crash")
            elif action == "close":
                c.close()
            elif action == "years":
                del c.vars[c.COOLDOWN]  # two years pass: the timed variable runs out
            else:
                c.lose()

        def legal(c, action):
            if action in ("crash", "scare"):
                return bool(c.queued)
            if action in ("close", "lose"):
                return bool(c.open)
            if action == "years":
                return c.COOLDOWN in c.vars
            return True

        def walk(c, seq):
            nonlocal runs
            if len(seq) == depth:
                runs += 1
                while c.queued or c.open:
                    if c.open:
                        c.close()
                    else:
                        c.fire(True)
                    if c.problems():
                        found.append((seq + ["drain"], c.problems()))
                        return
                for name in self.LEFTOVERS:
                    if name in c.vars and not c.lost:  # a lost copy's wait for the next send
                        found.append((seq + ["drain"], [f"{name} left over"]))
                return
            for action in actions:
                if legal(c, action):
                    nxt = copy.deepcopy(c)
                    step(nxt, action)
                    if nxt.problems():
                        runs += 1
                        found.append((seq + [action], nxt.problems()))
                        continue
                    walk(nxt, seq + [action])

        first = Country(**mutation)
        step(first, "wave")
        walk(first, ["wave"])
        return runs, found

    def test_no_sequence_of_waves_and_answers_breaks_the_block(self):
        runs, found = self.explore()
        self.assertGreater(runs, 1000)
        self.assertEqual(found[:5], [])

    def test_the_checks_bite(self):
        # Each mutation breaks one part of the block or the wave's count; the exploration must catch every one.
        reach = EFFECTS["banking_contagion_reach"]
        send_always = field(reach, "else")
        no_outcome = copy.deepcopy(reach)
        turned_away = field(no_outcome, "if")
        turned_away[:] = [item for item in turned_away if item[0] != "if"]
        no_clear = copy.deepcopy(reach)
        sending = field(no_clear, "else")
        sending[:] = [item for item in sending if item[0] != "banking_contagion_clear_stale"]
        after = field(MINOR_EVENTS[self.EVENT], "after")
        no_release = [item for item in after if "banking_contagion_pending" not in repr(item)]
        self.assertEqual(len(no_release), len(after) - 1)
        decide = EFFECTS["banking_contagion_decide"]
        scare_branch = next(i for i, (key, _, _) in enumerate(decide) if key == "else_if")
        no_cooldown = copy.deepcopy(decide)  # a shown scare starts no cooldown
        no_cooldown[scare_branch][2][:] = [i for i in no_cooldown[scare_branch][2] if i[0] != "set_variable"]
        always_shown = copy.deepcopy(decide)  # the cooldown never holds a scare back
        always_shown[scare_branch][2][0] = ("limit", "=", [("has_variable", "=", "contagion_crash")])
        keeps_mark = copy.deepcopy(decide)  # a held-back scare leaves the country marked
        keeps_mark[-1][2][:] = [i for i in keeps_mark[-1][2] if i[0] != "if"]
        mutations = {
            "the spread ignores the mark": {"mutations": {"banking_contagion_reach": send_always}},
            # a scare held back is the fifth step: a wave, its scare, the answer, a second wave, its scare
            "a shown scare starts no cooldown": {"depth": 5, "mutations": {"banking_contagion_decide": no_cooldown}},
            "the cooldown holds nothing back": {"depth": 5, "mutations": {"banking_contagion_decide": always_shown}},
            "a held-back scare keeps the mark": {"depth": 5, "mutations": {"banking_contagion_decide": keeps_mark}},
            "a turned-away reach records no outcome": {"mutations": {"banking_contagion_reach": no_outcome}},
            "a new copy keeps a lost one's leftovers": {"mutations": {"banking_contagion_reach": no_clear}},
            "after keeps the mark": {"after": no_release},
            "an origin is not marked counted": {"init": [
                item for item in EFFECTS["banking_crisis_wave_init"]
                if item[0] == "every_country" or "banking_crisis_wave_counted" not in repr(item)]},
        }
        for name, mutation in mutations.items():
            with self.subTest(mutation=name):
                runs, found = self.explore(**{"depth": 4, **mutation})
                self.assertTrue(found, f"{name}: {runs} sequences, nothing caught")
        # The self-check is what catches the first in game: two copies open, BROKEN once.
        c = Country(mutations={"banking_contagion_reach": send_always})
        c.new_wave()
        c.spread()
        c.new_wave()
        self.assertEqual(c.spread(), "sent")
        c.fire(1)
        c.fire(0)
        broken = c.lines("BROKEN", "contagion_one_open")
        self.assertEqual(len(broken), 1)
        self.assertIn("open=", broken[0])

    def test_the_spread_reaches_through_the_block(self):
        # The every_country limit keeps its wave test (Country.spread models it), and its roll's
        # success runs banking_contagion_reach, which alone sends the event.
        spread = EFFECTS["banking_cycle_spread_contagion"]
        loop = field(field(spread, "custom_tooltip"), "every_country")
        self.assertIn(("NOT", "=", [("banking_crisis_wave_reached", "=", "yes")]), field(loop, "limit"))
        body = field(loop, "random")
        self.assertIn(("banking_contagion_reach", "=", "yes"), body)
        self.assertNotIn("trigger_event", repr(body))
        self.assertNotIn("banking_crisis_wave_hit", repr(body))
        self.assertNotIn("banking_contagion_pending", repr(EFFECTS["banking_crisis_wave_init"]))

    def test_the_mark_outlasts_a_live_copy(self):
        # The event waits a week, then stays open at most its duration in months (scripting_best_practices
        # .md: "An event's duration is in months"); the mark must run longer, from the send and again from
        # the opening, or a second copy can be sent to a country still holding one.
        mark = field(EFFECTS["banking_contagion_mark_pending"], "set_variable")
        days = int(field(mark, "days"))
        event = MINOR_EVENTS[self.EVENT]
        months = int(field(event, "duration"))
        decide = [val for key, _, val in field(EFFECTS["banking_contagion_decide"], "if") if key == "trigger_event"]
        send_on = int(field(decide[0], "days"))  # the hidden event sends the popup a day on
        immediate = [key for key, _, _ in field(event, "immediate")]
        self.assertIn("banking_contagion_mark_pending", immediate)
        send = field(EFFECTS["banking_contagion_reach"], "else")
        self.assertIn(("banking_contagion_mark_pending", "=", "yes"), send)
        wait = int(field(field(send, "trigger_event"), "days")) + send_on
        self.assertEqual(wait, 7)  # the popup lands a week after the reach, with or without the hidden event
        self.assertGreater(days, wait + 31 * months)

    def test_nothing_in_after_fires_an_event_at_once(self):
        # A trigger_event with no delay runs the event inside the calling effect; inside .7's `after` it
        # would run another copy's immediate between the verdict and the removals.
        after = repr(field(MINOR_EVENTS[self.EVENT], "after"))
        self.assertNotIn("trigger_event", after)

        def fired(body):
            for key, _, val in body:
                if key == "trigger_event":
                    yield val
                elif isinstance(val, list):
                    yield from fired(val)
        for name in ("banking_contagion_reach", "banking_contagion_selfcheck_close", "banking_contagion_clear_stale"):
            for event in fired(REGISTRY.body(name)):
                self.assertTrue(field(event, "days"), name)
        self.assertEqual(len(list(fired(REGISTRY.body("banking_contagion_reach")))), 1)

    def test_the_roll_sets_the_marks_the_stub_sets(self):
        check = EFFECTS["banking_contagion_crash_check"]
        at = next(i for i, (key, _, val) in enumerate(check)
                  if key == "if" and field(val, "limit") == [("var:contagion_crash", ">", "0")])
        crash = check[at][2]
        self.assertIn(("set_variable", "=", [("name", "=", "banking_crisis_wave_crashed"), ("value", "=", "1")]), crash)
        self.assertEqual(check[at + 1][0], "else")
        scare = check[at + 1][2]
        self.assertIn(("set_variable", "=", [("name", "=", "banking_crisis_wave_scared"), ("value", "=", "1")]), scare)

    def test_a_revolution_clears_the_mark(self):
        # The winner inherits the loser's variables but not its events: je_banking_cycle's immediate,
        # which runs again on the inherited copy, removes the mark.
        je = definitions("common/journal_entries/je_banking.txt")["je_banking_cycle"]
        immediate = field(je, "immediate")
        clear = [val for key, _, val in immediate
                 if key == "if" and field(val, "limit") == [("has_variable", "=", "banking_contagion_pending")]]
        self.assertEqual(len(clear), 1)
        self.assertIn(("remove_variable", "=", "banking_contagion_pending"), clear[0])


class ContagionScareCooldownTest(unittest.TestCase):
    """A scare is shown once in two years (owner, 2026-10-22): "if a spread happens and it does not
    trigger a crash, do not fire the relevant event unless it has been at least 2 years since the
    last time it fired."

    The roll used to be event .7's own immediate, too late to keep the popup from opening, so the
    hidden event .9 rolls first (banking_contagion_decide) and sends .7 on only when a crash, or a
    scare out of its cooldown, is to be shown. These run that effect, with the roll replaced by its
    outcome (CRASH_ROLL) or, where a test says so, the real one.
    """
    EVENT = "minor_events_timelineextended.7"
    DECIDER = "minor_events_timelineextended.9"
    COOLDOWN = "banking_contagion_scare_cooldown"
    # a country mid-wave: reached, with the mark the spread set when it sent the hidden event
    SENT = {"banking_crisis_wave_hit": 1, "banking_contagion_pending": 1}

    def decide(self, crashed, variables=None):
        roll = substitute(copy.deepcopy(CRASH_ROLL), {"ROLL": int(crashed), "SEVERITY": 40})
        it = Interp({**self.SENT, **(variables or {})}, overrides={"banking_contagion_crash_check": roll})
        it.execute(copy.deepcopy(EFFECTS["banking_contagion_decide"]))
        return it

    def popups(self, it):
        return [(e["id"], e["popup"], e["days"]) for e in it.events]

    def test_a_crash_is_always_shown_and_does_not_touch_the_cooldown(self):
        for cooling in (False, True):
            with self.subTest(cooling=cooling):
                it = self.decide(1, {self.COOLDOWN: 1} if cooling else None)
                self.assertEqual(self.popups(it), [(self.EVENT, "yes", "1")])
                self.assertEqual(it.scopes, {"contagion_crashed": "ROOT"})  # the title reads it when queued
                self.assertEqual(self.COOLDOWN in it.vars, cooling)
                self.assertIn("banking_contagion_pending", it.vars)  # the popup answers for the country

    def test_a_scare_out_of_cooldown_is_shown_and_starts_it(self):
        it = self.decide(0)
        self.assertEqual(self.popups(it), [(self.EVENT, "yes", "1")])
        self.assertIn(self.COOLDOWN, it.vars)
        self.assertNotIn("contagion_crashed", it.scopes)
        self.assertIn("banking_contagion_pending", it.vars)

    def test_a_scare_in_the_cooldown_is_not_shown_and_frees_the_country(self):
        it = self.decide(0, {self.COOLDOWN: 1, "contagion_crash": 0, "banking_contagion_turned_away": 2})
        self.assertEqual(it.events, [])
        self.assertIn(self.COOLDOWN, it.vars)  # it only runs out; a held-back scare does not restart it
        self.assertIn("banking_crisis_wave_scared", it.vars)  # a survivor, for the Great Depression
        self.assertIn("banking_crisis_wave_hit", it.vars)
        for name in ("banking_contagion_pending", "contagion_crash", "banking_contagion_turned_away"):
            self.assertNotIn(name, it.vars)
        self.assertEqual(it.scopes, {})

    def test_two_years_is_730_days_on_a_country_variable(self):
        decide = EFFECTS["banking_contagion_decide"]
        sets = [val for key, _, val in field(decide, "else_if") if key == "set_variable"]
        self.assertEqual(len(sets), 1)
        self.assertEqual((field(sets[0], "name"), field(sets[0], "days")), (self.COOLDOWN, "730"))
        self.assertEqual(TRIGGERS["banking_contagion_scare_cooling"], [("has_variable", "=", self.COOLDOWN)])

    def test_the_cooldown_is_set_where_a_scare_is_sent_and_nowhere_else(self):
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").glob("*.txt")):
            text = path.read_text(encoding="utf-8-sig")
            if self.COOLDOWN in text:
                self.assertIn(path.name, ("banking_cycle_effects.txt", "banking_policy_triggers.txt"), path)
        self.assertEqual((ROOT / "common/scripted_effects/banking_cycle_effects.txt").read_text(
            encoding="utf-8-sig").count(f"name = {self.COOLDOWN}"), 1)

    def test_a_forced_scare_is_held_to_the_same_rule(self):
        # The real roll, for a country that crashed within the year (banking_contagion_scare_only): its
        # first contagion scare is shown, the next one inside two years is not.
        def decide(variables):
            it = Interp({**self.SENT, "bubble_pressure": 90, "banking_crashed_last_year": 1, **variables},
                        values=ContagionScareOnlyTest.VALUES, picks=[], others=ContagionScareOnlyTest.ORIGIN,
                        trigger_values=ContagionScareOnlyTest.PINNED,
                        overrides=ContagionScareOnlyTest.ASIDE)
            it.execute(copy.deepcopy(EFFECTS["banking_contagion_decide"]))
            return it
        first = decide({})
        self.assertEqual(self.popups(first), [(self.EVENT, "yes", "1")])
        self.assertEqual(first.vars["contagion_crash"], 0)
        self.assertNotIn("crash_severity", first.vars)
        second = decide({self.COOLDOWN: 1})
        self.assertEqual(second.events, [])
        self.assertNotIn("contagion_crash", second.vars)

    def test_the_spread_sends_the_hidden_event_and_only_it_sends_the_popup(self):
        hidden = MINOR_EVENTS[self.DECIDER]
        self.assertEqual(field(hidden, "hidden"), "yes")
        self.assertEqual(field(hidden, "immediate"), [("banking_contagion_decide", "=", "yes")])
        send = field(EFFECTS["banking_contagion_reach"], "else")
        self.assertEqual(field(field(send, "trigger_event"), "id"), self.DECIDER)
        self.assertEqual(field(field(send, "trigger_event"), "days"), "6")  # and the popup's day makes the week
        sent = []
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").glob("*.txt")):
            text = path.read_text(encoding="utf-8-sig")
            for match in re.finditer(r"trigger_event\s*=\s*\{[^}]*?id\s*=\s*minor_events_timelineextended\.7\b", text):
                sent.append(path.name)
        self.assertEqual(sent, ["banking_cycle_effects.txt", "banking_cycle_effects.txt"])  # a crash, a scare

    def test_the_popup_rolls_only_for_a_copy_nobody_rolled_for(self):
        immediate = field(MINOR_EVENTS[self.EVENT], "immediate")
        stub = parse_body("set_variable = { name = contagion_crash value = 1 }")
        # sent by the hidden event: contagion_crash is set, and the popup keeps that roll
        rolled = Interp({"contagion_crash": 0}, overrides={"banking_contagion_crash_check": stub})
        rolled.execute(copy.deepcopy(immediate))
        self.assertNotIn("banking_contagion_crash_check", rolled.ran)
        self.assertEqual(rolled.vars["contagion_crash"], 0)
        # sent by an older build: no roll yet, so it rolls
        legacy = Interp({}, overrides={"banking_contagion_crash_check": stub})
        legacy.execute(copy.deepcopy(immediate))
        self.assertEqual(legacy.ran.count("banking_contagion_crash_check"), 1)
        self.assertEqual(legacy.scopes, {"contagion_crashed": "ROOT"})

    def test_the_exploration_covers_the_cooldown_running_out(self):
        # A scare, the cooldown, another scare held back, then two years and the scare shows again.
        c = Country()
        c.new_wave()
        c.spread()
        self.assertEqual(c.fire(False), "popup")
        c.close()
        self.assertIn(self.COOLDOWN, c.vars)
        c.new_wave()
        self.assertEqual(c.spread(), "sent")
        self.assertEqual(c.fire(False), "silent")
        self.assertEqual(c.problems(), [])
        for name in ContagionBlockTest.LEFTOVERS:
            self.assertNotIn(name, c.vars)
        c.new_wave()
        self.assertEqual(c.spread(), "sent")  # freed: the held-back scare left no mark
        self.assertEqual(c.fire(True), "popup")  # a crash is shown inside the cooldown
        c.close()
        del c.vars[self.COOLDOWN]
        c.new_wave()
        c.spread()
        self.assertEqual(c.fire(False), "popup")
        self.assertEqual(c.problems(), [])
        self.assertIn(self.COOLDOWN, c.vars)


class LocTest(unittest.TestCase):
    def test_the_no_raise_line_has_text(self):
        text = (ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml").read_text(
            encoding="utf-8-sig")
        self.assertRegex(text, r"(?m)^ CRASH_NO_RAISE_DESC:0 \"")


if __name__ == "__main__":
    unittest.main()
