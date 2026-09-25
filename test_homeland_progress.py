"""Offline scenarios against the actual homeland scripts (not an engine test).

A deliberately small interpreter handles only the vocabulary these scripts use.
Unknown statements fail so a new mechanic cannot silently skip test coverage.
"""
import operator
import unittest
from decimal import Decimal
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent


def parse(path):
    tokens = ParadoxFileParser().tokenize(
        (ROOT / path).read_text(encoding="utf-8-sig"))
    index = 0
    def block():
        nonlocal index
        result = []
        while index < len(tokens):
            key = tokens[index]
            index += 1
            if key == "}":
                return result
            op = tokens[index]
            index += 1
            value = tokens[index]
            index += 1
            if value == "{":
                if tokens[index] != "}" and tokens[index + 1] not in ("=", "<", ">", ">=", "<=", "?=", "!="):
                    value = []
                    while tokens[index] != "}":
                        value.append(tokens[index])
                        index += 1
                    index += 1
                else:
                    value = block()
            result.append((key, op, value))
        return result
    return {k: v for k, _, v in block()}


def get(block, key, default=None):
    return next((v for k, _, v in block if k == key), default)


def obj(kind, **fields):
    return dict(kind=kind, variables={}, lists={}, **fields)


class Script:
    def __init__(self, state):
        self.root = state
        self.scopes = {}
        self.temporary = {}
        self.notifications = []
        self.triggers = parse("common/scripted_triggers/homeland_triggers.txt")
        self.effects = parse("common/scripted_effects/homeland_effects.txt")
        self.values = parse("common/script_values/homeland_values.txt")
        self.values.update(parse("common/script_values/extra_script_values.txt"))
        self.pulse = parse("common/on_actions/extra_on_actions.txt")["te_homeland_monthly"]

    def ref(self, text, current, previous=None):
        if isinstance(text, list):
            return self.value(text, current, previous)
        if text == "yes":
            return True
        if text == "no":
            return False
        try:
            return Decimal(text)
        except Exception:
            pass
        if "." in text:
            first, rest = text.split(".", 1)
            return self.ref(rest, self.ref(first, current, previous), current)
        if text == "ROOT":
            return self.root
        if text == "PREV":
            return previous
        if text.startswith("scope:"):
            return self.scopes.get(text[6:])
        if text.startswith("var:"):
            return current["variables"].get(text[4:])
        if text.startswith("modifier:"):
            return current["modifiers"].get(text[9:], Decimal(0))
        if text in self.values:
            return self.value(self.values[text], current, previous)
        return current[text]

    def condition(self, block, current, previous=None, mode="AND"):
        answers = []
        for key, op, value in block:
            if key in ("variable", "list", "limit"):
                continue
            if key in ("NOT", "AND", "OR"):
                answer = self.condition(value, current, previous, key)
            elif key in self.triggers:
                answer = self.condition(self.triggers[key], current, previous)
                answer = answer == (value == "yes")
            elif key in ("any_scope_culture", "any_scope_state", "any_in_list"):
                candidates = self.items(key, value, current)
                answer = any(self.condition(value, item, current) for item in candidates)
            elif key == "has_variable_list":
                answer = bool(current["lists"].get(value))
            elif key == "has_tag":
                answer = value in current["tags"]
            elif key == "exists":
                answer = self.ref(value, current, previous) is not None
            elif key == "is_primary_culture_of":
                answer = current["name"] in self.ref(value, current, previous)["primary"]
            elif key == "has_homeland":
                answer = current["name"] in self.ref(value, current, previous)["state_region"]["homelands"]
            elif key == "culture_percent_state":
                culture = self.ref(get(value, "target"), current, previous)
                _, compare, threshold = next(x for x in value if x[0] == "value")
                answer = self.compare(compare, current["shares"].get(culture["name"], Decimal(0)),
                                      self.ref(threshold, current, previous))
            elif isinstance(value, list):
                target = self.ref(key, current, previous)
                answer = target is not None and self.condition(value, target, current)
            else:
                answer = self.compare(op, self.ref(key, current, previous),
                                      self.ref(value, current, previous))
            answers.append(answer)
        return (not any(answers)) if mode == "NOT" else any(answers) if mode == "OR" else all(answers)

    @staticmethod
    def compare(op, a, b):
        if isinstance(a, dict) or isinstance(b, dict):
            if op != "=":
                raise AssertionError(op)
            return a is b
        return {"=": operator.eq, ">=": operator.ge, "<": operator.lt,
                ">": operator.gt, "<=": operator.le}[op](a, b)

    def items(self, key, block, current):
        if key.endswith("scope_culture"):
            return self.root["cultures"]
        if key.endswith("scope_state"):
            return current["states"]
        if get(block, "variable") is not None:
            return list(current["lists"].get(get(block, "variable"), []))
        return list(self.temporary.get(get(block, "list"), []))

    def value(self, block, current, previous=None):
        if not isinstance(block, list):
            return self.ref(block, current, previous)
        total = Decimal(0)
        taken = False
        for key, _, value in block:
            if key in ("if", "else_if"):
                if key == "if":
                    taken = False
                if not taken and self.condition(get(value, "limit", []), current, previous):
                    # Script-value branches mutate the surrounding accumulator.
                    total = self.arithmetic(value, current, previous, total)
                    taken = True
            elif key != "limit":
                total = self.arithmetic([(key, "=", value)], current, previous, total)
        return total

    def arithmetic(self, block, current, previous, total):
        for key, _, value in block:
            if key == "limit":
                continue
            if key == "every_in_list":
                for item in self.items(key, value, current):
                    total = self.arithmetic([x for x in value if x[0] != "variable"], item, current, total)
                continue
            other = self.ref(value, current, previous)
            if key == "value":
                total = other
            elif key == "add":
                total += other
            elif key == "multiply":
                total *= other
            elif key == "divide":
                total /= other
            elif key == "min":
                total = max(total, other)
            elif key == "max":
                total = min(total, other)
            else:
                raise AssertionError(f"Unknown arithmetic: {key}")
        return total

    def run(self, block, current, previous=None):
        taken = False
        for key, _, value in block:
            if key in ("limit", "variable", "list"):
                continue
            if key in ("if", "else_if"):
                if key == "if":
                    taken = False
                if not taken and self.condition(get(value, "limit", []), current, previous):
                    self.run(value, current, previous)
                    taken = True
            elif key in self.effects:
                self.run(self.effects[key], current, previous)
            elif key in ("every_scope_culture", "every_in_list"):
                candidates = [x for x in self.items(key, value, current)
                              if self.condition(get(value, "limit", []), x, current)]
                for item in candidates:
                    self.run(value, item, current)
            elif key == "save_scope_as":
                self.scopes[value] = current
            elif key == "create_container":
                project = obj("container", tags=get(value, "tags"), destroyed=False)
                self.scopes[get(value, "save_scope_as")] = project
            elif key == "set_variable":
                current["variables"][get(value, "name")] = self.ref(get(value, "value"), current, previous)
            elif key == "change_variable":
                current["variables"][get(value, "name")] += self.ref(get(value, "add"), current, previous)
            elif key == "remove_variable":
                current["variables"].pop(value, None)
            elif key == "add_to_variable_list":
                current["lists"].setdefault(get(value, "name"), []).append(
                    self.ref(get(value, "target"), current, previous))
            elif key == "add_to_temporary_list":
                self.temporary.setdefault(value, []).append(current)
            elif key == "remove_list_variable":
                target = self.ref(get(value, "target"), current, previous)
                entries = current["lists"][get(value, "name")]
                entries[:] = [x for x in entries if x is not target]
            elif key == "destroy_container":
                current["destroyed"] = True
            elif key in ("add_homeland", "remove_homeland"):
                name = self.ref(value, current, previous)["name"]
                if key == "add_homeland":
                    current["homelands"].add(name)
                else:
                    current["homelands"].remove(name)
            elif key == "post_notification":
                self.notifications.append(value)
            elif isinstance(value, list):
                self.run(value, self.ref(key, current, previous), current)
            else:
                raise AssertionError(f"Unknown effect: {key}")

    def month(self):
        self.scopes = {}
        self.temporary = {}
        self.run(get(self.pulse, "effect"), self.root)

    def projects(self, mode):
        return self.root["lists"].get(f"te_homeland_{mode}_projects", [])


class HomelandProgressTests(unittest.TestCase):
    def make(self, shares=None, homelands=None, primary=("a",), speed=0, removal=".1"):
        owner = obj("country", primary=set(primary), legitimacy=50,
                    modifiers={"country_homelands_can_change_bool": True})
        state = obj("state", owner=owner, turmoil=Decimal(0),
                    shares={k: Decimal(str(v)) for k, v in (shares or {"a": ".7", "b": ".05", "c": ".05"}).items()},
                    cultures=[obj("culture", name=n) for n in ("a", "b", "c")],
                    modifiers={"state_homeland_creation_threshold_add": Decimal(".6"),
                               "state_homeland_removal_threshold_add": Decimal(removal),
                               "state_homeland_change_speed_mult": Decimal(speed)})
        region = obj("region", states=[state], homelands=set(("b", "c") if homelands is None else homelands))
        state["state_region"] = region
        return Script(state)

    def test_parallel_creation_and_removal_complete_at_120_months(self):
        sim = self.make()
        for _ in range(119):
            sim.month()
        self.assertEqual(len(sim.projects("removal")), 2)
        self.assertEqual([p["variables"]["te_homeland_progress"] for p in sim.projects("removal")], [1190, 1190])
        self.assertEqual(sim.root["state_region"]["homelands"], {"b", "c"})
        sim.month()
        self.assertEqual(sim.root["state_region"]["homelands"], {"a"})
        self.assertEqual(sim.notifications.count("homeland_removed"), 2)
        self.assertEqual(len(sim.projects("creation")) + len(sim.projects("removal")), 0)

    def test_new_candidate_does_not_inherit_progress(self):
        sim = self.make(shares={"a": ".7", "b": ".05", "c": ".2"})
        for _ in range(60):
            sim.month()
        sim.root["shares"]["c"] = Decimal(".05")
        sim.month()
        progress = {p["variables"]["te_homeland_culture"]["name"]: p["variables"]["te_homeland_progress"]
                    for p in sim.projects("removal")}
        self.assertEqual(progress, {"b": 610, "c": 10})

    def test_unlock_and_split_pause_then_resume(self):
        sim = self.make()
        sim.month()
        sim.root["owner"]["modifiers"]["country_homelands_can_change_bool"] = False
        sim.month()
        self.assertEqual(sim.projects("creation")[0]["variables"]["te_homeland_progress"], 10)
        sim.root["owner"]["modifiers"]["country_homelands_can_change_bool"] = True
        sim.root["state_region"]["states"].append(obj("state", owner=obj("country")))
        sim.month()
        self.assertEqual(sim.projects("creation")[0]["variables"]["te_homeland_progress"], 10)
        sim.root["state_region"]["states"].pop()
        sim.month()
        self.assertEqual(sim.projects("creation")[0]["variables"]["te_homeland_progress"], 20)

    def test_owner_change_restarts_projects(self):
        sim = self.make()
        for _ in range(20):
            sim.month()
        old = sim.projects("removal")[0]
        sim.root["owner"] = obj("country", primary={"a"}, legitimacy=50,
                                modifiers={"country_homelands_can_change_bool": True})
        sim.month()
        self.assertTrue(old["destroyed"])
        self.assertEqual([p["variables"]["te_homeland_progress"] for p in sim.projects("removal")], [10, 10])

    def test_threshold_boundaries_and_zero_removal(self):
        sim = self.make(shares={"a": ".6", "b": ".1", "c": "0"}, removal="0")
        sim.month()
        self.assertEqual(len(sim.projects("creation")), 1)
        self.assertEqual(len(sim.projects("removal")), 0)
        sim.root["modifiers"]["state_homeland_removal_threshold_add"] = Decimal(".1")
        sim.month()
        self.assertEqual(len(sim.projects("removal")), 1)  # c only; b is exactly the threshold

    def test_lost_eligibility_resets_only_affected_culture(self):
        sim = self.make()
        sim.month()
        old = sim.projects("removal")[0]
        sim.root["shares"]["b"] = Decimal(".2")
        sim.month()
        self.assertTrue(old["destroyed"])
        self.assertEqual(len(sim.projects("removal")), 1)
        self.assertEqual(sim.projects("removal")[0]["variables"]["te_homeland_progress"], 20)

    def test_decree_rate_and_live_status(self):
        sim = self.make(speed=3)
        self.assertEqual(sim.value(sim.values["te_homeland_creation_status"], sim.root), 6)
        for _ in range(29):
            sim.month()
        self.assertNotIn("a", sim.root["state_region"]["homelands"])
        self.assertEqual(sim.value(sim.values["te_homeland_creation_status"], sim.root), 5)
        sim.month()
        self.assertIn("a", sim.root["state_region"]["homelands"])
        sim.root["owner"]["modifiers"]["country_homelands_can_change_bool"] = False
        self.assertEqual(sim.value(sim.values["te_homeland_creation_status"], sim.root), 1)

    def test_multiple_creation_candidates_progress_together(self):
        sim = self.make(shares={"a": ".5", "b": ".4", "c": ".05"}, homelands={"c"}, primary=("a", "b"))
        sim.root["modifiers"]["state_homeland_creation_threshold_add"] = Decimal(".3")
        sim.month()
        self.assertEqual(len(sim.projects("creation")), 2)
        self.assertEqual([p["variables"]["te_homeland_progress"] for p in sim.projects("creation")], [10, 10])

    def test_rate_multipliers_and_clamps(self):
        sim = self.make(speed=3)
        sim.root["owner"]["legitimacy"] = 75
        sim.root["turmoil"] = Decimal(".5")
        self.assertEqual(sim.value(sim.values["te_homeland_annual_progress"], sim.root), 75)
        sim.root["modifiers"]["state_homeland_change_speed_mult"] = Decimal(100)
        self.assertEqual(sim.value(sim.values["te_homeland_annual_progress"], sim.root), 95)
        sim.root["modifiers"]["state_homeland_change_speed_mult"] = Decimal(-100)
        sim.root["owner"]["legitimacy"] = 0
        self.assertEqual(sim.value(sim.values["te_homeland_annual_progress"], sim.root), 1)

    def test_container_gui_root_and_primary_status_change(self):
        sim = self.make()
        sim.month()
        project = sim.projects("removal")[0]
        state = sim.root
        sim.root = project  # ScriptContainer.MakeScope.ScriptValue roots here.
        self.assertEqual(sim.value(sim.values["te_homeland_project_eligible"], project), 1)
        self.assertEqual(sim.value(sim.values["te_homeland_project_progress_pct"], project),
                         Decimal(10) / 12)
        state["owner"]["primary"].add("b")
        self.assertEqual(sim.value(sim.values["te_homeland_project_progress_pct"], project), 0)
        sim.root = state
        sim.month()
        self.assertTrue(project["destroyed"])
        self.assertEqual(len(sim.projects("removal")), 1)

    def test_live_blocker_messages(self):
        sim = self.make(shares={"a": ".4", "b": ".2", "c": ".2"})
        status = sim.values["te_homeland_creation_status"]
        self.assertEqual(sim.value(status, sim.root), 4)
        sim.root["state_region"]["homelands"].add("a")
        self.assertEqual(sim.value(status, sim.root), 3)
        sim.root["state_region"]["states"].append(obj("state", owner=obj("country")))
        self.assertEqual(sim.value(status, sim.root), 2)

    @staticmethod
    def shown(sim):
        """The tile's visibility values, as the state panel reads them."""
        names = ("te_homeland_relevant", "te_homeland_pause_status",
                 "te_homeland_creation_shown", "te_homeland_removal_shown")
        return tuple(sim.value(sim.values[name], sim.root) for name in names)

    def test_tile_hides_tracks_with_no_culture(self):
        # "a" is primary and already has a homeland; "b" and "c" have none.
        sim = self.make(homelands={"a"})
        self.assertEqual(self.shown(sim), (0, 0, 0, 0))
        sim.root["owner"]["modifiers"]["country_homelands_can_change_bool"] = False
        self.assertEqual(self.shown(sim), (0, 1, 0, 0))  # no pause line either
        sim.root["owner"]["modifiers"]["country_homelands_can_change_bool"] = True
        sim.root["state_region"]["homelands"].add("b")
        self.assertEqual(self.shown(sim), (1, 0, 0, 1))  # removal only
        sim.root["state_region"]["homelands"].discard("a")
        self.assertEqual(self.shown(sim), (1, 0, 1, 1))

    def test_threshold_blocked_track_is_still_shown(self):
        sim = self.make(shares={"a": ".4", "b": ".2", "c": ".2"}, homelands={"b"})
        self.assertEqual(self.shown(sim), (1, 0, 1, 1))
        self.assertEqual(sim.value(sim.values["te_homeland_creation_status"], sim.root), 4)
        self.assertEqual(sim.value(sim.values["te_homeland_removal_status"], sim.root), 4)

    def test_pause_shows_only_tracks_with_kept_progress(self):
        sim = self.make()
        sim.root["owner"]["modifiers"]["country_homelands_can_change_bool"] = False
        self.assertEqual(self.shown(sim), (1, 1, 0, 0))
        sim.root["owner"]["modifiers"]["country_homelands_can_change_bool"] = True
        sim.month()
        sim.root["state_region"]["states"].append(obj("state", owner=obj("country")))
        self.assertEqual(self.shown(sim), (1, 2, 1, 1))
        sim.root["state_region"]["states"].pop()
        self.assertEqual(self.shown(sim), (1, 0, 1, 1))

    def test_stale_projects_stay_shown_until_cleanup(self):
        sim = self.make(homelands={"a", "b", "c"})  # removal projects only
        sim.month()
        self.assertEqual(len(sim.projects("removal")), 2)
        sim.root["state_region"]["homelands"].difference_update({"b", "c"})
        # Both projects are now invalid and no culture applies, but their
        # "no longer eligible" rows stay up until the next pulse clears them.
        self.assertEqual(self.shown(sim), (1, 0, 0, 1))
        sim.month()
        self.assertEqual(self.shown(sim), (0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
