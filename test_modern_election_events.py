"""`events/modern_election_events.txt`: the gates and options that keep each
event's premise true (the script gaps found by the text rewrite, #1551)."""
import re
import unittest

import scripts.analysis.event_guarantees as eg


def _event(event_id):
    found = eg.find_events(event_id)
    assert [e[0] for e in found] == [event_id], found
    return found[0][2]


def _options(body):
    """Each top-level ``option = { ... }`` block's body, in order."""
    out = []
    for m in re.finditer(r"^\toption = \{", body, re.M):
        start = m.end() - 1
        out.append(body[start + 1:eg.block_end(body, start)])
    return out


def _norm(text):
    return " ".join(re.sub(r"#[^\n]*", "", text).split())


class GateTests(unittest.TestCase):
    def test_voice_of_the_nation_needs_radio_and_no_television(self):
        trigger = eg.read_trigger(_event("modern_election_events.11"))
        self.assertIn("radio", trigger["required"])
        self.assertEqual(sorted(trigger["absent"]), ["television", "television_broadcasting"])

    def test_neural_voting_needs_the_interfaces(self):
        trigger = eg.read_trigger(_event("modern_election_events.33"))
        self.assertIn("brain_computer_interfaces", trigger["required"])

    def test_lab_grown_food_needs_its_technology(self):
        trigger = eg.read_trigger(_event("modern_election_events.34"))
        self.assertIn("lab-grown_food", trigger["required"])

    def test_economic_miracle_needs_a_running_cycle(self):
        body = _norm(_event("modern_election_events.15"))
        self.assertIn("te_banking_cycle_running = yes", body)
        self.assertNotIn("te_banking_cycle_running = no", body)


class OptionTests(unittest.TestCase):
    def test_transparency_legislation_is_not_gated_on_decolonization(self):
        options = _options(_event("modern_election_events.25"))
        self.assertNotIn("decolonization", _norm(options[2]))
        self.assertNotIn("trigger = {", _norm(options[2]).split("ai_chance")[0])

    def test_pilot_program_hides_under_universal_basic_income(self):
        options = _options(_event("modern_election_events.29"))
        self.assertIn("trigger = { NOT = { has_law_or_variant = law_type:law_universal_basic_income } }",
                      _norm(options[2]))

    def test_calmer_broadcast_does_not_help_the_opposition(self):
        options = _options(_event("modern_election_events.11"))
        self.assertIn("scope:govt_party = { add_momentum", _norm(options[2]))
        self.assertNotIn("scope:opp_party", _norm(options[2]))

    def test_foot_in_mouth_names_follow_whose_blunder(self):
        options = _options(_event("modern_election_events.9"))
        for option, key in zip(options[:2], ("9.a", "9.b")):
            text = _norm(option)
            self.assertIn(f"text = modern_election_events.{key}_own", text)
            self.assertIn(f"text = modern_election_events.{key} ", text)

    def test_ai_does_not_prefer_letting_our_own_blunder_run(self):
        options = _options(_event("modern_election_events.9"))
        self.assertIn("modifier = { trigger = { exists = scope:own_gaffe_party } add = -4 }",
                      _norm(options[0]))


if __name__ == "__main__":
    unittest.main()
