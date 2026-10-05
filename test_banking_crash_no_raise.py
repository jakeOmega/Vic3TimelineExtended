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


class Interp:
    def __init__(self, variables, laws=()):
        self.vars = dict(variables)
        self.laws = set(laws)
        self.tooltips = []

    def num(self, token):
        if isinstance(token, list):
            raise AssertionError("script-value blocks are not modelled")
        if token.startswith("var:"):
            return float(self.vars.get(token[4:], 0))  # an unrecorded var: reads 0
        return float(token)

    def check(self, body, mode="AND"):
        answers = []
        for key, op, val in body:
            if key in ("AND", "OR", "NOT"):
                answer = self.check(val, key)
            elif key == "has_variable":
                answer = val in self.vars
            elif key == "has_law":
                answer = val.removeprefix("law_type:") in self.laws
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
            elif key in INERT_EFFECTS:
                continue
            elif key in REGISTRY:
                if key in EFFECTS or REGISTRY.writes_cycle(key):
                    params = {k: v for k, _, v in val} if isinstance(val, list) else {}
                    self.execute(substitute(copy.deepcopy(REGISTRY.body(key)), params))
                # else: an effect that never writes the cycle; nothing to model
            else:
                raise AssertionError(f"unmodelled effect {key}")


def run(effect, variables, laws=(), **params):
    it = Interp(variables, laws)
    it.execute(substitute(copy.deepcopy(EFFECTS[effect]), params))
    return it


def option_bodies(event_id):
    options = []
    for key, _, val in MINOR_EVENTS[event_id]:
        if key == "option":
            options.append((field(val, "name"), [i for i in val if i[0] not in OPTION_META]))
    return options


def run_option(body, variables, laws=()):
    it = Interp(variables, laws)
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
            for crashed, laws in itertools.product((0, 1), ContagionScareTest.LAWS):
                for severity in (5, 45, 85):
                    with self.subTest(option=name, contagion_crash=crashed, laws=laws, sev=severity):
                        for value, momentum in itertools.product(VALUES, MOMENTA):
                            start = {"finance_cycle_value": value, "finance_cycle_momentum": momentum,
                                     "bubble_pressure": 30, "contagion_crash": crashed,
                                     "crash_severity": severity}
                            it = run_option(body, start, laws)
                            self.assertLessEqual(it.vars["finance_cycle_value"], value + EPS)
                            self.assertLessEqual(it.vars["finance_cycle_momentum"], momentum + EPS)
                            for prior in PRIOR_VARS:
                                self.assertNotIn(prior, it.vars)


class LocTest(unittest.TestCase):
    def test_the_no_raise_line_has_text(self):
        text = (ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml").read_text(
            encoding="utf-8-sig")
        self.assertRegex(text, r"(?m)^ CRASH_NO_RAISE_DESC:0 \"")


if __name__ == "__main__":
    unittest.main()
