"""The Ukrainian and Byelorussian Cultural Renaissances close when their culture
has no homeland left (Workshop report, 2026-11-08).

Vanilla opens each entry on the culture's fervor and involves the owners of the
culture's homeland states. The mod's dynamic homelands can remove every one, so
common/journal_entries/te_vanilla_cultural_renaissances.txt injects a hidden
invalid outcome that ends the entry once no state is a homeland of the culture
(te_homeland_none_left, common/scripted_triggers/homeland_triggers.txt).

Vanilla's side is read from the committed vanilla_parsed/ snapshot, so these run
in CI without the game.

Run: python3 -m unittest test_cultural_renaissance_homelands -v
"""

import json
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
JE_FILE = ROOT / "common/journal_entries/te_vanilla_cultural_renaissances.txt"
TRIGGERS = ROOT / "common/scripted_triggers/homeland_triggers.txt"
SELFCHECK = ROOT / "common/on_actions/te_renaissance_selfcheck_on_actions.txt"
PLAYTEST = ROOT / "docs/testing/homelands-playtest.md"
VANILLA_JES = ROOT / "vanilla_parsed/common/journal_entries.json"
LOC_DIR = ROOT / "localization/english"

ENTRIES = {
    "je_ukraine_cultural_renaissance": "ukrainian",
    "je_belarus_cultural_renaissance": "byelorussian",
}
MARKER = "te_renaissance_homeless_fired"
CONCLUSION = "te_renaissance_no_homeland_conclusion_desc"


def norm(value):
    return json.loads(json.dumps(value))


def pairs(value):
    if isinstance(value, list) and value and isinstance(value[0], list):
        return value
    return [value]


def flags(outcome):
    if "flags" not in outcome:
        return []
    return [f for p in pairs(outcome["flags"]) for f in p[1]]


def parse_file(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(path), apply_directives=False)
    return {key: norm(value) for key, value in parser.data.items()}


def text(path):
    return re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))


class InjectedOutcomeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.parsed = parse_file(JE_FILE)
        cls.vanilla = json.loads(VANILLA_JES.read_text(encoding="utf-8"))

    def test_each_entry_gets_one_hidden_invalid_outcome(self):
        self.assertEqual(sorted(self.parsed), sorted("INJECT:" + e for e in ENTRIES))
        for entry, culture in ENTRIES.items():
            with self.subTest(entry=entry):
                body = self.parsed["INJECT:" + entry][1]
                self.assertEqual(list(body), ["outcome"])
                outcomes = pairs(body["outcome"])
                self.assertEqual(len(outcomes), 1)
                outcome = outcomes[0][1]
                self.assertEqual(sorted(flags(outcome)), ["hidden", "invalid_outcome"])
                self.assertEqual(outcome["conclusion_desc"], ["=", CONCLUSION])
                self.assertEqual(outcome["trigger"],
                                 ["=", {"te_homeland_none_left": ["=", {"CULTURE": ["=", culture]}]}])
                self.assertEqual(outcome["effect"], ["=", {"set_global_variable": ["=", MARKER]}])

    def test_vanilla_has_no_invalid_outcome_of_its_own(self):
        # An entry may have one invalid outcome; a vanilla patch that adds one
        # makes the injected copy a second.
        for entry in ENTRIES:
            with self.subTest(entry=entry):
                outcomes = [p[1] for p in pairs(norm(self.vanilla[entry])[1]["outcome"])]
                self.assertFalse([o for o in outcomes if "invalid_outcome" in flags(o)])

    def test_the_trigger_is_vanilla_involvement_for_no_country(self):
        # Vanilla involves a country that owns a state in one of the culture's
        # homelands; the trigger holds when no country could be.
        for entry, culture in ENTRIES.items():
            with self.subTest(entry=entry):
                involved = norm(self.vanilla[entry])[1]["should_be_involved"]
                self.assertEqual(involved, ["=", {"any_scope_state": ["=", {"state_region": ["=", {
                    "is_homeland": ["=", "cu:" + culture]}]}]}])
        trigger = " ".join(text(TRIGGERS).split())
        self.assertIn("te_homeland_none_left = { NOT = { any_country = { any_scope_state = { "
                      "state_region = { is_homeland = cu:$CULTURE$ } } } } }", trigger)

    def test_the_conclusion_has_loc(self):
        found = any(re.search(rf"^\s+{CONCLUSION}:\d*\s+\"", p.read_text(encoding="utf-8-sig"), re.M)
                    for p in LOC_DIR.glob("*.yml"))
        self.assertTrue(found)


class SelfCheckTest(unittest.TestCase):

    def test_the_selfcheck_reads_the_marker_and_both_entries(self):
        check = " ".join(text(SELFCHECK).split())
        self.assertIn("on_monthly_pulse = { on_actions = { te_renaissance_homeless_selfcheck } }", check)
        self.assertIn(f"has_global_variable = {MARKER}", check)
        for entry, culture in ENTRIES.items():
            self.assertIn(f"any_country = {{ has_journal_entry = {entry} }} "
                          f"te_homeland_none_left = {{ CULTURE = {culture} }}", check)
        for verdict in ("TE_SELF_CHECK OK renaissance_homeless_outcome",
                        "TE_SELF_CHECK BROKEN renaissance_homeless_outcome"):
            self.assertIn(verdict, check)
        self.assertIn("renaissance_homeless_outcome", PLAYTEST.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
