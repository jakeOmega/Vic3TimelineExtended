"""Evaluate the real retooling waiver script against AI and human buildings.

Engine inputs are stubbed; expectations come from the rule's gameplay contract.
This checks the owner scope, old saves, and the existing level-zero/railway
exceptions without needing a Victoria 3 install.
"""
import itertools
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
AI_ONLY = "free_market_construction_no_ai_retooling"
GLOBAL_WAIVERS = {
    "free_market_construction_no_retooling",
    "free_market_construction_no_maintenance",
}


def load(path):
    parser = ParadoxFileParser()
    parsed, remaining = parser.parse_object(
        parser.tokenize("{" + (ROOT / path).read_text(encoding="utf-8-sig") + "}")
    )
    assert not remaining
    return parsed


def entries(block):
    for item in block if isinstance(block, list) else [block]:
        for key, (op, value) in item.items():
            yield key, op, value


class RetoolingScript:
    def __init__(self, rule):
        self.rule = rule
        self.triggers = load("common/scripted_triggers/te_construction_market_triggers.txt")
        self.effect = load("common/scripted_effects/extra_effects.txt")[
            "te_remove_waived_pm_retooling"][1]

    def condition(self, block, scope):
        return all(self.one_condition(key, op, value, scope)
                   for key, op, value in entries(block))

    def one_condition(self, key, op, value, scope):
        if key == "OR":
            return any(self.one_condition(k, o, v, scope) for k, o, v in entries(value))
        if key == "AND":
            return self.condition(value, scope)
        if key == "NOT":
            return not self.condition(value, scope)
        if key in ("owner", "state"):
            return self.condition(value, scope[key])
        if key == "has_game_rule":
            return value == self.rule
        if key == "has_modifier":
            return value in scope["modifiers"]
        if key == "is_ai":
            return scope["is_ai"] == (value == "yes")
        if key == "is_building_type":
            return scope["type"] == value
        if key == "has_variable":
            return value in scope["variables"]
        if key == "level" and op == "=":
            return scope["level"] == int(value)
        if key in self.triggers:
            return self.condition(self.triggers[key][1], scope) == (value == "yes")
        raise AssertionError(f"Unhandled trigger: {key} {op} {value}")

    def apply(self, scope, block=None):
        for key, _, value in entries(self.effect if block is None else block):
            if key == "if":
                if self.condition(value["limit"][1], scope):
                    self.apply(scope, {k: v for k, v in value.items() if k != "limit"})
            elif key == "remove_modifier":
                scope["modifiers"].discard(value)
            else:
                raise AssertionError(f"Unhandled effect: {key}")


def building(ai, railway=False, marker=False, level=3, retooling=True):
    return {
        "owner": {"is_ai": ai},
        "state": {"variables": {"te_rail_retool_waive"} if marker else set()},
        "type": "building_railway" if railway else "building_steel_mill",
        "level": level,
        "modifiers": {"normal_maintenance"} | ({"pm_retooling"} if retooling else set()),
    }


class ConstructionRetoolingTests(unittest.TestCase):
    def test_rule_owner_and_existing_exceptions(self):
        rules = [None, "free_market_construction_enabled", AI_ONLY,
                 *sorted(GLOBAL_WAIVERS), "free_market_construction_disabled"]
        for rule in rules:
            script = RetoolingScript(rule)
            for ai, railway, marker, zero, retooling in itertools.product((False, True), repeat=5):
                with self.subTest(rule=rule, ai=ai, railway=railway,
                                  marker=marker, zero=zero, retooling=retooling):
                    scope = building(ai, railway, marker, 0 if zero else 3, retooling)
                    waived = (zero or rule in GLOBAL_WAIVERS or (rule == AI_ONLY and ai)
                              or (railway and marker))
                    script.apply(scope)
                    self.assertEqual("pm_retooling" in scope["modifiers"], retooling and not waived)
                    self.assertIn("normal_maintenance", scope["modifiers"])

    def test_owner_control_is_rechecked_for_delayed_cleanup(self):
        script = RetoolingScript(AI_ONLY)
        scope = building(True)
        script.apply(scope)
        self.assertNotIn("pm_retooling", scope["modifiers"])
        # Taking control does not restore a removed penalty; a new PM change pays.
        scope["owner"]["is_ai"] = False
        script.apply(scope)
        self.assertNotIn("pm_retooling", scope["modifiers"])
        scope["modifiers"].add("pm_retooling")
        script.apply(scope)
        self.assertIn("pm_retooling", scope["modifiers"])
        # Relinquishing control also changes the next cleanup's decision.
        scope["owner"]["is_ai"] = True
        script.apply(scope)
        self.assertNotIn("pm_retooling", scope["modifiers"])

    def test_ai_setting_keeps_enabled_production_method_flags(self):
        rule = load("common/game_rules/extra_game_rules.txt")["free_market_construction_rule"][1]
        def flags(setting):
            return {v for k, _, v in entries(rule[setting][1]) if k == "flag"}
        self.assertEqual(rule["default"][1], "free_market_construction_enabled")
        self.assertEqual(flags(AI_ONLY) - {AI_ONLY},
                         flags("free_market_construction_enabled") - {"free_market_construction_enabled"})
        loc = (ROOT / "localization/english/te_game_rules_l_english.yml").read_text(encoding="utf-8-sig")
        for suffix in ("", "_desc"):
            self.assertIn(f" setting_{AI_ONLY}{suffix}:0 ", loc)


if __name__ == "__main__":
    unittest.main()
