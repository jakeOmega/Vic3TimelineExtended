"""Single-Party State's dominant party for the mod's parties (#1908).

Vanilla 1.15.2's single_party_state.8 names the party a Single-Party State
keeps, with one option per vanilla party; te_single_party_state.1 is its twin
for the parties the mod adds. Each mod party needs five pieces that name it,
and nothing in the engine reports a missing one: an option in the event that
calls vanilla's set_sps_dominant_party_effect, the two scopes that effect
reads, the amendment it attaches, the join_weight term and the
available_for_interest_group gate. This holds every party in common/parties/
to all five, the amendments to vanilla's (so a vanilla re-tune shows up here),
and the event's senders to the variable vanilla's event reads.
"""

import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "generators"))

import vanilla_parsed  # noqa: E402
from ig_feminism import field_lines  # noqa: E402
from paradox_file_parser import ParadoxFileParser  # noqa: E402

PARTIES_DIR = os.path.join(ROOT, "common", "parties")
AMENDMENTS = os.path.join(ROOT, "common", "amendments", "te_sps_party_dominance.txt")
EVENT_FILE = os.path.join(ROOT, "events", "te_single_party_state_events.txt")
TRIGGERS = os.path.join(ROOT, "common", "scripted_triggers", "te_single_party_state_triggers.txt")
ON_ACTIONS = os.path.join(ROOT, "common", "on_actions", "te_single_party_state_on_actions.txt")
SNAPSHOT_AMENDMENTS = os.path.join(ROOT, "vanilla_parsed", "common", "amendments.json")
LOC_DIR = os.path.join(ROOT, "localization", "english")

# The vanilla amendment the mod's three copy.
VANILLA_TEMPLATE = "amendment_agrarian_party_dominance"


def _read(path):
    with open(path, encoding="utf-8-sig") as file:
        return file.read()


def _strip_comments(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _norm(value):
    return json.dumps(vanilla_parsed.encode(value), sort_keys=True)


def _mod_parties():
    """Party type -> file text, for the parties the mod defines (not the
    generated INJECT file, which restates vanilla's)."""
    parties = {}
    for name in sorted(os.listdir(PARTIES_DIR)):
        if not name.endswith(".txt"):
            continue
        text = _read(os.path.join(PARTIES_DIR, name))
        for match in re.finditer(r"^([a-z_]+_party) = \{", _strip_comments(text), re.M):
            parties[match.group(1)] = text
    return parties


def _stem(party_type):
    return party_type[: -len("_party")]


def _event_block(text, event_id):
    lines = field_lines(text, re.escape(event_id))
    if not lines:
        raise AssertionError(f"{event_id} not found")
    return "\n".join(lines)


def _loc_values():
    values = {}
    for name in os.listdir(LOC_DIR):
        if name.endswith(".yml"):
            for match in re.finditer(r'^ ([\w.]+):\d* "(.*)"\s*$', _read(os.path.join(LOC_DIR, name)), re.M):
                values[match.group(1)] = match.group(2)
    return values


class ModPartyPiecesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parties = _mod_parties()
        cls.event = _strip_comments(_event_block(_read(EVENT_FILE), "te_single_party_state.1"))

    def test_the_mod_defines_parties(self):
        self.assertEqual(
            set(self.parties), {"green_party", "populist_party", "technocratic_party"},
            "the mod's parties changed: a new one needs the pieces this file checks",
        )

    def test_mod_party_trigger_lists_every_mod_party(self):
        body = "\n".join(field_lines(_strip_comments(_read(TRIGGERS)), "te_sps_is_mod_party"))
        self.assertEqual(set(re.findall(r"is_party_type = (\w+)", body)), set(self.parties))

    def test_event_offers_every_mod_party(self):
        loc = _loc_values()
        for party in self.parties:
            stem = _stem(party)
            with self.subTest(party=party):
                self.assertRegex(self.event, rf"set_sps_dominant_party_effect = \{{ PARTY = {stem} \}}")
                # vanilla's effect reads scope:sps_<PARTY>_ig and scope:sps_<PARTY>_party
                self.assertRegex(self.event, rf"save_scope_as = sps_{stem}_ig\b")
                self.assertRegex(self.event, rf"save_scope_as = sps_{stem}_party\b")
                self.assertRegex(self.event, rf"is_party_type = {party}\b")
                # once in the option's trigger, once in the cancellation_trigger
                self.assertEqual(
                    len(re.findall(rf"te_sps_twin_option_valid = \{{ PARTY = {stem} \}}", self.event)), 2,
                )
                names = [
                    loc.get(key, "")
                    for key in re.findall(r"name = (te_single_party_state\.1\.\w+)", self.event)
                ]
                self.assertTrue(
                    any(f"sParty('sps_{stem}_party')" in value for value in names),
                    f"no option text names scope:sps_{stem}_party",
                )

    def test_every_option_has_text(self):
        loc = _loc_values()
        for key in re.findall(r"\b(te_single_party_state\.1\.\w+)", self.event):
            with self.subTest(key=key):
                self.assertIn(key, loc)

    def test_join_weight_carries_the_dominance_term(self):
        for party, text in self.parties.items():
            stem = _stem(party)
            body = "\n".join(field_lines(_strip_comments(text), "join_weight"))
            with self.subTest(party=party):
                self.assertRegex(
                    body,
                    rf"ig_is_member_of_dominant_party = \{{ PARTY = {stem} \}}\s*\}}\s*"
                    rf"add = \{{\s*value = 1000\s*desc = \"amendment_{stem}_party_dominance\"",
                )

    def test_available_for_interest_group_opens_to_the_dominant_party(self):
        for party, text in self.parties.items():
            stem = _stem(party)
            body = "\n".join(field_lines(_strip_comments(text), "available_for_interest_group"))
            with self.subTest(party=party):
                self.assertRegex(
                    body,
                    rf"^trigger_if = \{{\s*limit = \{{\s*ig_is_member_of_dominant_party = "
                    rf"\{{ PARTY = {stem} \}}\s*\}}\s*always = yes\s*\}}\s*trigger_else = \{{",
                )


class AmendmentTest(unittest.TestCase):
    def test_each_amendment_copies_vanilla(self):
        with open(SNAPSHOT_AMENDMENTS, encoding="utf-8") as file:
            snapshot = vanilla_parsed.decode(json.load(file))
        self.assertIn(VANILLA_TEMPLATE, snapshot, "vanilla renamed or dropped its dominance amendments")
        parser = ParadoxFileParser()
        parser.parse_file(AMENDMENTS)
        expected = set(f"amendment_{_stem(p)}_party_dominance" for p in _mod_parties())
        self.assertEqual(set(parser.data), expected)
        for name in sorted(expected):
            with self.subTest(amendment=name):
                self.assertNotIn(name, snapshot, "vanilla defines this amendment now: drop the mod's copy")
                self.assertEqual(
                    _norm(parser.data[name]), _norm(snapshot[VANILLA_TEMPLATE]),
                    f"differs from vanilla's {VANILLA_TEMPLATE}: re-base the copy",
                )

    def test_each_amendment_has_a_name_and_description(self):
        loc = _loc_values()
        for party in _mod_parties():
            name = f"amendment_{_stem(party)}_party_dominance"
            with self.subTest(amendment=name):
                self.assertIn(name, loc)
                self.assertIn(f"{name}_desc", loc)


class SendersTest(unittest.TestCase):
    """The twin and vanilla's single_party_state.8 are both answered by setting
    sps_dominant_party_ig_var, so one must never be answered after the other:
    each sender marks the country before it sends; the start sender clears what
    an earlier enactment left; a checkpoint that fires .8 with a vanilla party
    to offer hands the choice to .8, which closes an open twin and stops the
    monthly offers in a mixed government."""

    SENDERS = ("te_sps_dominance_on_enactment_started", "te_sps_dominance_monthly")

    @classmethod
    def setUpClass(cls):
        cls.text = _strip_comments(_read(ON_ACTIONS))
        cls.event = _strip_comments(_event_block(_read(EVENT_FILE), "te_single_party_state.1"))

    def _block(self, name):
        return "\n".join(field_lines(self.text, name))

    def test_hooked_to_vanilla_on_actions(self):
        for on_action, handler in (
            ("on_law_enactment_started", "te_sps_dominance_on_enactment_started"),
            ("on_monthly_pulse_country", "te_sps_dominance_monthly"),
            ("on_law_checkpoint_advance", "te_sps_dominance_on_checkpoint"),
            ("on_law_checkpoint_debate", "te_sps_dominance_on_checkpoint"),
            ("on_law_checkpoint_success", "te_sps_dominance_on_checkpoint"),
        ):
            with self.subTest(on_action=on_action):
                block = self._block(on_action)
                self.assertRegex(block, rf"on_actions = \{{\s*{handler}\s*\}}")
                self.assertNotRegex(block, r"\beffect = \{", "an effect block replaces vanilla's")

    def test_each_sender_marks_before_it_sends(self):
        for handler in self.SENDERS:
            block = self._block(handler)
            with self.subTest(handler=handler):
                mark = block.find("name = te_sps_dominance_pending")
                send = block.find("id = te_single_party_state.1")
                self.assertGreaterEqual(mark, 0)
                self.assertGreater(send, mark)
                self.assertRegex(block, r"id = te_single_party_state\.1\s*popup = yes")

    def test_only_the_senders_send(self):
        self.assertEqual(self.text.count("id = te_single_party_state.1"), len(self.SENDERS))

    def test_start_sender_clears_what_an_earlier_enactment_left(self):
        block = self._block("te_sps_dominance_on_enactment_started")
        send = block.find("trigger_event")
        for name in ("sps_dominant_party_ig_var", "te_sps_dominance_pending", "te_sps_left_to_vanilla"):
            with self.subTest(variable=name):
                clear = block.find(f"remove_variable = {name}")
                self.assertGreaterEqual(clear, 0)
                self.assertGreater(send, clear)

    def test_monthly_sender_stays_away_from_a_choice_left_to_vanilla(self):
        block = self._block("te_sps_dominance_monthly")
        for line in (
            "NOT = { has_variable = sps_dominant_party_ig_var }",
            "NOT = { has_variable = te_sps_dominance_pending }",
            "te_sps_mod_party_in_government = yes",
        ):
            with self.subTest(line=line):
                self.assertIn(line, block)
        self.assertRegex(
            block,
            r"OR = \{\s*te_sps_vanilla_party_in_government = no\s*"
            r"NOT = \{ has_variable = te_sps_left_to_vanilla \}\s*\}",
        )

    def test_checkpoint_hands_the_choice_to_vanilla(self):
        block = self._block("te_sps_dominance_on_checkpoint")
        self.assertIn("NOT = { has_variable = sps_dominant_party_ig_var }", block)
        self.assertIn("te_sps_vanilla_party_in_government = yes", block)
        self.assertIn("set_variable = te_sps_left_to_vanilla", block)

    def test_event_closes_once_the_choice_is_vanillas(self):
        cancel = "\n".join(field_lines(self.event, "cancellation_trigger"))
        self.assertIn("has_variable = sps_dominant_party_ig_var", cancel)
        self.assertRegex(
            cancel,
            r"AND = \{\s*has_variable = te_sps_left_to_vanilla\s*"
            r"te_sps_vanilla_party_in_government = yes\s*\}",
        )
        # the option that leaves the choice to vanilla's event says so the same way
        self.assertRegex(self.event, r"set_variable = te_sps_left_to_vanilla")


if __name__ == "__main__":
    unittest.main()
