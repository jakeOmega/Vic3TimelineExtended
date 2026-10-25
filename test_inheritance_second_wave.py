"""Inheritance second-wave generation events (docs/superpowers/archive/specs/2026-10-08-inheritance-laws-design.md § 11).

What the engine would never report:

- An event no pulse rolls, or one rolled without its law's generation clock.
- An answer that moves Wealth Concentration without saying by how much (a
  variable change renders nothing in a tooltip), or whose tooltip names a
  different number from the one the script moves.
- The First Cohort coming twice in one tenure of the Birthright Endowment, or
  never again after the Endowment is repealed and attached afresh.
- A modifier an answer adds with no name in the loc.

No game install needed.
"""

import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
EVENTS = os.path.join(REPO, "events", "inheritance_events.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "te_inheritance_on_actions.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_inheritance_effects.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "te_inheritance_triggers.txt")
MODIFIERS = os.path.join(REPO, "common", "static_modifiers", "te_inheritance_modifiers.txt")

# event: (the law or amendment trigger, its sub-action)
SECOND_WAVE = {
    14: ("has_law = law_type:law_state_universal_heir", "te_inh_generation_universal_heir"),
    15: ("has_law = law_type:law_non_inheritable_usage_rights", "te_inh_generation_possession_by_use"),
    16: ("te_inh_has_birthright_endowment = yes", "te_inh_first_cohort"),
}
MODIFIERS_ADDED = ("inh_estates_audited", "inh_estates_overlooked", "inh_commune_repartition",
                   "inh_holding_continuity", "inh_cohort_schooled", "inh_cohort_enterprise", "inh_cohort_spent")


def _read(path):
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def _block(text, name):
    """The text of the top-level `name = {` block, braces balanced."""
    match = re.search(r"^%s = \{" % re.escape(name), text, re.M)
    if match is None:
        raise AssertionError("%s not found" % name)
    depth = 0
    for i in range(text.index("{", match.start()), len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : i + 1]
    raise AssertionError("%s is unbalanced" % name)


def _loc_lines():
    lines = {}
    for path in glob.glob(os.path.join(REPO, "localization", "english", "**", "*.yml"), recursive=True):
        for line in _read(path).splitlines():
            match = re.match(r"\s+([A-Za-z0-9_.\-]+):\d*\s", line)
            if match:
                lines[match.group(1)] = line
    return lines


class SecondWaveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = _read(EVENTS)
        cls.loc = _loc_lines()

    def _event(self, n):
        return _block(self.events, "inheritance_events.%d" % n)

    def _trigger(self, n):
        event = self._event(n)
        start = event.index("\ttrigger = {")
        end = event.index("\timmediate = {") if "\timmediate = {" in event else event.index("\toption = {")
        return event[start:end]

    def test_each_event_rolls_from_its_own_sub_action(self):
        on_actions = _read(ON_ACTIONS)
        pulse = _block(on_actions, "on_yearly_pulse_country")
        for n, (_, sub_action) in SECOND_WAVE.items():
            with self.subTest(event=n):
                self.assertIn(sub_action, pulse)
                self.assertIn("inheritance_events.%d" % n, _block(on_actions, sub_action))

    def test_the_laws_events_wait_a_generation(self):
        for n in (14, 15):
            trigger = self._trigger(n)
            with self.subTest(event=n):
                self.assertIn(SECOND_WAVE[n][0], trigger)
                self.assertIn("te_inh_generation_due = yes", trigger)
                self.assertIn("cooldown = { years = 25 }", self._event(n))

    def test_the_first_cohort_comes_once_a_tenure(self):
        trigger = self._trigger(16)
        self.assertIn(SECOND_WAVE[16][0], trigger)
        self.assertIn("var:te_inh_endowment_years >= 5", trigger)
        self.assertIn("NOT = { has_variable = te_inh_first_cohort_paid }", trigger)
        self.assertIn("set_variable = te_inh_first_cohort_paid", self._event(16))
        counter = _block(_read(EFFECTS), "te_inh_count_endowment_years")
        lapsed = counter[counter.index("\telse = {"):]
        self.assertIn("remove_variable = te_inh_first_cohort_paid", lapsed)
        self.assertIn("remove_variable = te_inh_endowment_years", lapsed)
        self.assertIn("te_inh_count_endowment_years = yes", _block(_read(EFFECTS), "te_inh_yearly_update"))
        self.assertIn("amendment_type:amendment_birthright_endowment",
                      _block(_read(TRIGGERS), "te_inh_has_birthright_endowment"))

    def test_score_moves_say_so_with_the_same_number(self):
        for n in SECOND_WAVE:
            for option in re.split(r"\n\toption = \{", self._event(n))[1:]:
                name = re.search(r"name = (\S+)", option).group(1)
                shift = re.search(r"custom_tooltip = \{\s*text = (\S+)\s*te_inh_shift_concentration = "
                                  r"\{ AMOUNT = (-?\d+) \}", option)
                with self.subTest(option=name):
                    if "te_inh_shift_concentration" not in option:
                        continue
                    self.assertIsNotNone(shift, "the score moves outside a custom_tooltip")
                    key, amount = shift.groups()
                    line = self.loc[key]
                    self.assertIn("#v %d#!" % abs(int(amount)), line)
                    self.assertIn("falls" if int(amount) < 0 else "rises", line)

    def test_every_event_has_loc(self):
        for n in SECOND_WAVE:
            for suffix in ("t", "d", "f", "a", "b"):
                self.assertIn("inheritance_events.%d.%s" % (n, suffix), self.loc)

    def test_modifiers_exist_and_are_named(self):
        modifiers = _read(MODIFIERS)
        for name in MODIFIERS_ADDED:
            with self.subTest(modifier=name):
                _block(modifiers, name)
                self.assertIn(name, self.loc)
                self.assertIn(name + "_desc", self.loc)
        # A modifier that takes authority is a cost, never a negative add (CLAUDE.md).
        self.assertIn("country_authority_cost_add = 100", _block(modifiers, "inh_estates_audited"))

    def test_every_answer_is_timed(self):
        # A modifier added without a duration needs a Nation tab registry line;
        # these are all timed.
        for n in SECOND_WAVE:
            for name in re.findall(r"add_modifier = \{ name = (inh_\w+)([^}]*)\}", self._event(n)):
                self.assertRegex(name[1], r"years = \d+", name[0])


if __name__ == "__main__":
    unittest.main()
