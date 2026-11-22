"""The ministry enactment events' side effects fit the option that carries them.

events/ministry_law_events.txt pairs each option's enactment modifier with a
"domain side-effect". The pools' design (law_events_on_actions.txt,
ministry_law_enactment_modifiers.txt) fixes which way it points:

- a stall option's side effect is a cost (a stall is a checkpoint the law lost);
- in a debate, the option that pushes the law pays a cost and the concession
  that slows it is given a benefit.

Issue #1614 found four that pointed the wrong way or named the wrong thing:
.29.b paid .10.a's benefit on a stall, .42 gave the treasury saving to the
phased wind-down under a comment about swift cuts, the dovish envoys of .44.b
slowed relations, and turning refugees away in .50.b sped them. It also found
.9.c reading two saved scopes of which only one is guaranteed.

The static modifiers' icons carry the sign (`..._positive.dds` /
`..._negative.dds`), which is what the tooltip shows the player. No game
install needed.
"""

import glob
import os
import re
import unittest

from test_law_checkpoint_pools import (
    ON_ACTIONS,
    REPO,
    STATIC_MODIFIERS,
    SUCCESS,
    _parse,
    _pool,
    _values,
)

EVENTS = os.path.join(REPO, "events", "ministry_law_events.txt")
NAMESPACE = "ministry_law_events."


def _country_modifiers(option):
    """Names of the modifiers an option adds to the country itself."""
    return [next(_values(mod["name"])) for mod in _values(option.get("add_modifier", []))]


def _enactment_modifiers(option):
    return [next(_values(mod["name"])) for mod in _values(option.get("add_enactment_modifier", []))]


class MinistrySideEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        on_actions = _parse(ON_ACTIONS)
        cls.pools = {
            checkpoint: [
                event
                for event in _pool(on_actions, f"on_law_checkpoint_{checkpoint}")
                if event.startswith(NAMESPACE)
            ]
            for checkpoint in ("debate", "stall")
        }
        cls.icons, cls.success = {}, {}
        for path in glob.glob(STATIC_MODIFIERS):
            for name, node in _parse(path).items():
                for value in _values(node):
                    if not isinstance(value, dict):
                        continue
                    if "icon" in value:
                        cls.icons[name] = str(next(_values(value["icon"])))
                    if SUCCESS in value:
                        cls.success[name] = float(next(_values(value[SUCCESS])))
        cls.events = _parse(EVENTS)
        with open(EVENTS, encoding="utf-8-sig") as f:
            cls.text = re.sub(r"#[^\n]*", "", f.read())

    def _options(self, event):
        return {
            str(next(_values(option["name"]))).rsplit(".", 1)[-1]: option
            for option in _values(self.events[event][1]["option"])
        }

    def _sign(self, modifier):
        icon = self.icons.get(modifier)
        self.assertIsNotNone(icon, f"{modifier} has no icon to read its sign from")
        if icon.endswith("_positive.dds"):
            return 1
        if icon.endswith("_negative.dds"):
            return -1
        return 0

    def test_pools_are_read(self):
        self.assertGreater(len(self.pools["stall"]), 10)
        self.assertGreater(len(self.pools["debate"]), 10)

    def test_a_stall_option_pays_no_benefit(self):
        for event in self.pools["stall"]:
            for letter, option in self._options(event).items():
                for modifier in _country_modifiers(option):
                    with self.subTest(event=event, option=letter, modifier=modifier):
                        self.assertLess(
                            self._sign(modifier), 1,
                            f"{event}.{letter} is a stall option and adds the benefit {modifier}")

    def test_a_debate_concession_pays_no_cost(self):
        # The other half (the push pays a cost) holds for .40 onward but not
        # for the first debates (.5, .10, .11, .13, .15), whose push option
        # carries the law's own benefit, so it is not asserted here.
        for event in self.pools["debate"]:
            for letter, option in self._options(event).items():
                push = sum(self.success.get(name, 0) for name in _enactment_modifiers(option))
                if push >= 0:
                    continue
                for modifier in _country_modifiers(option):
                    with self.subTest(event=event, option=letter, modifier=modifier):
                        self.assertGreater(
                            self._sign(modifier), -1,
                            f"{event}.{letter} concedes and also pays the cost {modifier}")

    def test_swift_dissolution_is_the_option_that_saves_money(self):
        options = self._options(NAMESPACE + "42")
        self.assertIn("ministry_dissolution_swift", _enactment_modifiers(options["a"]))
        self.assertIn("add_treasury", options["a"])
        self.assertNotIn("add_treasury", options["b"])

    def test_envoys_and_resettlement_do_not_invert_relations(self):
        # Seeking agreement first must not slow relations; turning refugees
        # away must not warm other countries to us.
        dovish = self._options(NAMESPACE + "44")["b"]
        self.assertIn("ministry_fa_dovish", _enactment_modifiers(dovish))
        self.assertNotIn("te_diplomatic_relations_drain", _country_modifiers(dovish))
        restrictive = self._options(NAMESPACE + "50")["b"]
        self.assertIn("ministry_refugee_restrictive", _enactment_modifiers(restrictive))
        self.assertNotIn("te_diplomatic_relations_boost", _country_modifiers(restrictive))

    def test_capital_vs_labor_reads_its_saved_groups_only_where_they_exist(self):
        # `ig:X ?= { save_scope_as = S }` saves nothing in a country without
        # the group. The other events that read such a scope require the group
        # in their trigger; .9 does not, and its option .c tests only the
        # favored side, so both reads must be `scope:S ?= {`.
        start = self.text.index(NAMESPACE + "9 = {")
        body = self.text[start:self.text.index(NAMESPACE + "10 = {")]
        saved = set(re.findall(r"ig:\w+\s*\?=\s*\{\s*save_scope_as\s*=\s*(\w+)", body))
        self.assertEqual(saved, {"trade_unions_ig", "industrialists_ig"})
        for scope in sorted(saved):
            with self.subTest(scope=scope):
                self.assertTrue(re.search(rf"scope:{scope}\s*\?=\s*\{{", body))
                self.assertEqual(
                    re.findall(rf"scope:{scope}\s*=\s*\{{", body), [],
                    f"scope:{scope} is entered without `?=`")


if __name__ == "__main__":
    unittest.main()
