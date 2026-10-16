"""The law-enactment checkpoint pools match what their events do to the law.

common/on_actions/law_events_on_actions.txt fires the mod's enactment events
from vanilla's three checkpoint on-actions, and the event window labels each
event with its checkpoint: advance, debate or stall. A stall is a checkpoint the
law lost, so a stall event whose options push the law turns the opposition's
roll into a bonus. Fourteen events from before issue #81 sat in the stall pool
that way (The Automation Question gave +10% or +2% success on a "stall"),
beside the stall events #81 wrote for the same laws. Every debate option pushed
the law too, so any checkpoint short of a stall helped it; since 2026-10-16
each debate offers a concession that slows the law in return for a benefit.
What these checks pin:

- every option of a stall-pool event slows the law (an enactment setback or a
  modifier with negative country_law_enactment_success_add) and none pushes it;
- no option of an advance-pool event slows the law;
- every debate-pool event has an option that pushes the law and one that
  slows it;
- no event sits in two pools, whose rules exclude each other;
- every event a pool names exists.

No game install needed.
"""

import glob
import os
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "law_events_on_actions.txt")
STATIC_MODIFIERS = os.path.join(REPO, "common", "static_modifiers", "*.txt")
SUCCESS = "country_law_enactment_success_add"


def _parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(path, apply_directives=False)
    return parser.data


def _values(node):
    """Every value under a key, whether the parser kept one or a list."""
    for _, value in node if isinstance(node, list) else [node]:
        yield value


def _pool(on_actions, name):
    events = []
    for random_events in _values(on_actions[name][1]["random_events"]):
        for weighted in random_events.values():
            events.extend(_values(weighted))
    return events


def _enactment_effects(block):
    """(modifier names, setback total, phase total) anywhere in an option."""
    modifiers, setbacks, phases = [], 0, 0
    for key, node in block.items():
        for value in _values(node):
            if key == "add_enactment_modifier":
                modifiers.extend(_values(value["name"]))
            elif key == "add_enactment_setback":
                setbacks += int(value)
            elif key == "add_enactment_phase":
                phases += int(value)
            elif isinstance(value, dict) and key != "trigger":
                inner = _enactment_effects(value)
                modifiers.extend(inner[0])
                setbacks += inner[1]
                phases += inner[2]
    return modifiers, setbacks, phases


class LawCheckpointPoolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        on_actions = _parse(ON_ACTIONS)
        cls.pools = {
            checkpoint: _pool(on_actions, f"on_law_checkpoint_{checkpoint}")
            for checkpoint in ("advance", "debate", "stall")
        }
        cls.success = {}
        for path in glob.glob(STATIC_MODIFIERS):
            for name, node in _parse(path).items():
                for value in _values(node):
                    if isinstance(value, dict) and SUCCESS in value:
                        cls.success[name] = float(next(_values(value[SUCCESS])))
        cls.events = {}
        namespaces = {event.split(".")[0] for pool in cls.pools.values() for event in pool}
        for namespace in namespaces:
            cls.events.update(_parse(os.path.join(REPO, "events", f"{namespace}.txt")))

    def _options(self, event):
        options = []
        for option in _values(self.events[event][1]["option"]):
            name = next(_values(option["name"]))
            if isinstance(name, dict):  # name = { trigger = { ... } text = ... }
                name = next(_values(name["text"]))
            options.append((name, _enactment_effects(option)))
        return options

    def _push_and_slow(self, effects):
        modifiers, setbacks, phases = effects
        pushes = phases > 0 or any(self.success.get(name, 0) > 0 for name in modifiers)
        slows = setbacks > 0 or any(self.success.get(name, 0) < 0 for name in modifiers)
        return pushes, slows

    def test_pool_events_exist(self):
        for checkpoint, pool in self.pools.items():
            for event in pool:
                with self.subTest(checkpoint=checkpoint, event=event):
                    self.assertIn(event, self.events)

    def test_pools_are_populated(self):
        for checkpoint, pool in self.pools.items():
            with self.subTest(checkpoint=checkpoint):
                self.assertGreater(len(pool), 10)

    def test_stall_options_slow_the_law(self):
        for event in self.pools["stall"]:
            for name, effects in self._options(event):
                pushes, slows = self._push_and_slow(effects)
                with self.subTest(event=event, option=name):
                    self.assertTrue(slows, f"{event} option {name} does not slow the law: {effects}")
                    self.assertFalse(pushes, f"{event} option {name} pushes the law: {effects}")

    def test_advance_options_do_not_slow_the_law(self):
        for event in self.pools["advance"]:
            for name, effects in self._options(event):
                _, slows = self._push_and_slow(effects)
                with self.subTest(event=event, option=name):
                    self.assertFalse(slows, f"{event} option {name} slows the law: {effects}")

    def test_debate_events_offer_a_push_and_a_concession(self):
        for event in self.pools["debate"]:
            shapes = [self._push_and_slow(effects) for _, effects in self._options(event)]
            with self.subTest(event=event):
                self.assertIn((True, False), shapes, f"{event} has no option that pushes the law")
                self.assertIn((False, True), shapes, f"{event} has no option that slows the law")

    def test_each_event_sits_in_one_pool(self):
        seen = {}
        for checkpoint, pool in self.pools.items():
            for event in pool:
                with self.subTest(event=event):
                    self.assertNotIn(event, seen, f"{event} is in the {seen.get(event)} and {checkpoint} pools")
                seen[event] = checkpoint

    def test_the_automation_question_is_a_debate(self):
        self.assertIn("extra_law_events.22", self.pools["debate"])
        self.assertNotIn("extra_law_events.22", self.pools["stall"])


if __name__ == "__main__":
    unittest.main()
