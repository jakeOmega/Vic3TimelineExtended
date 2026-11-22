"""Operation Polo offers a formed India only the holdout inside its core (2026-11-20).

`operation_polo_on_action` opens formation_te.10, whose first two options annex the target outright. Its test used to be
a shared border, a Muslim state religion and `NOT = { country_rank >= rank_value:minor_power }`, which an Unrecognized
Regional Power also passes, so an AI India annexed Persia whole, without a war, in game after game. The conditions are
now one scripted trigger, `te_operation_polo_target`, which also requires the target's capital to be in one of India's
core states (`te_is_india_core_state`). This test holds that state list to the formation's own, checks the rank gate
against vanilla's rank values, and checks that the on_action's test and pick both read the trigger.
"""
import json
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/te_operation_polo_triggers.txt"
FORMATION = ROOT / "common/country_formation/te_formable_countries.txt"
ON_ACTIONS = ROOT / "common/on_actions/extra_on_actions.txt"
RANKS = ROOT / "vanilla_parsed/common/country_ranks.json"
STATES = ROOT / "vanilla_parsed/history/states.json"


def parse_file(path):
    """The file's entries, with the parser's (op, value) tuples as lists."""
    parser = ParadoxFileParser()
    parser.parse_file(str(path), False)
    return json.loads(json.dumps(parser.data))


def body(entry):
    """The block of a `key = { ... }` entry, as the parser returns it (`["=", {...}]`)."""
    op, value = entry
    assert op == "=", entry
    return value


def values(block, key):
    """Every (op, value) the block holds for key, a repeated key included."""
    items = block.get(key, [])
    return items if items and isinstance(items[0], list) else ([items] if items else [])


class OperationPoloTargetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = parse_file(TRIGGERS)
        cls.target = body(cls.triggers["te_operation_polo_target"])

    def test_core_list_is_the_formation_states_list(self):
        core = body(body(self.triggers["te_is_india_core_state"])["OR"])
        listed = [value for op, value in values(core, "state_region")]
        self.assertTrue(all(op == "=" for op, _ in values(core, "state_region")))
        formation = body(parse_file(FORMATION)["BHA"])["states"][1]
        self.assertEqual(listed, [f"s:{state}" for state in formation],
                         "te_is_india_core_state must list BHA's formation states, in their order")
        self.assertIn("s:STATE_HYDERABAD", listed, "the Nizam's holdout is the case the event is for")

    def test_capital_must_be_in_the_core(self):
        self.assertEqual(body(self.target["capital"]), {"te_is_india_core_state": ["=", "yes"]})

    def test_no_1836_state_of_persia_afghanistan_or_oman_is_in_the_core(self):
        core = {value[2:] for _, value in values(body(body(self.triggers["te_is_india_core_state"])["OR"]),
                                                  "state_region")}
        states = json.loads(STATES.read_text(encoding="utf-8"))["00_states.txt"]
        for tag in ("PER", "KAB", "KAN", "HER", "OMA"):
            owned = {name for name, state in states.items()
                     if any(part["country"] == tag for part in state.get("parts", []))}
            with self.subTest(tag=tag):
                self.assertTrue(owned, f"{tag} owns states in 1836")
                self.assertEqual(owned & core, set())

    def test_rank_gate_admits_only_the_ranks_below_minor_power(self):
        ranks = {name: int(entry[1]["rank_value"][1])
                 for name, entry in json.loads(RANKS.read_text(encoding="utf-8")).items()}
        op, bound = self.target["country_rank"]
        self.assertTrue(bound.startswith("rank_value:"), bound)
        limit = ranks[bound.removeprefix("rank_value:")]
        passes = {"<=": lambda v: v <= limit, "<": lambda v: v < limit}[op]
        # Decentralized countries are refused by the trigger's own country-type test.
        admitted = {name for name, value in ranks.items() if passes(value) and name != "decentralized_power"}
        self.assertEqual(admitted, {"insignificant_power", "unrecognized_power"})
        self.assertGreater(ranks["unrecognized_regional_power"], limit,
                           "an Unrecognized Regional Power has a Minor Power's prestige thresholds")

    def test_on_action_test_and_pick_both_read_the_trigger(self):
        branch = body(body(body(parse_file(ON_ACTIONS)["operation_polo_on_action"])["effect"])["if"])
        test = body(body(branch["limit"])["any_country"])
        pick = body(body(branch["random_country"])["limit"])
        for name, block in (("any_country", test), ("random_country limit", pick)):
            with self.subTest(block=name):
                self.assertEqual(block, {"te_operation_polo_target": ["=", "yes"]})


if __name__ == "__main__":
    unittest.main()
