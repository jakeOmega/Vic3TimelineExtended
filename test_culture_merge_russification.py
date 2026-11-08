"""Tests for Russification's injected outcome (culture merges, plan Task 7).

Vanilla's Russification entry completes when 65% of the western borderlands' states
are at least 15% Russian (08_russification.txt). Once Russian pops merge into East
Slavic (cm_east_slavic) that share falls, and the entry could never complete. The
mod injects a second success outcome into the entry: vanilla's own, with the culture
test widened to Russian or East Slavic.

Files under test:
- common/journal_entries/te_vanilla_russification_merge.txt: INJECT:je_russification
  with the second success outcome.
- common/scripted_triggers/te_culture_merge_triggers.txt: te_cm_russification_state_ok
  (state) and te_cm_russification_complete (country).
- common/script_values/te_culture_merge_values.txt: te_cm_russian_or_east_slavic_share
  (state).

Vanilla's side is read from the committed vanilla_parsed/ snapshot, so the mirror tests
run in CI without the game. After a vanilla patch to the entry, rebuild the snapshot
(python3 vanilla_parsed.py build) and these tests say what the copy must follow.

Run: python3 -m unittest test_culture_merge_russification -v
"""

import copy
import json
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
JE_FILE = ROOT / "common/journal_entries/te_vanilla_russification_merge.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_culture_merge_triggers.txt"
VALUES = ROOT / "common/script_values/te_culture_merge_values.txt"
CULTURES = ROOT / "common/cultures/te_merged_cultures.txt"
VANILLA_JES = ROOT / "vanilla_parsed/common/journal_entries.json"
VANILLA_VALUES = ROOT / "vanilla_parsed/common/script_values.json"
VANILLA_CULTURES = ROOT / "vanilla_parsed/common/cultures.json"

ENTRY = "je_russification"
INJECT_KEY = "INJECT:" + ENTRY
SHARE = "te_cm_russian_or_east_slavic_share"
STATE_OK = "te_cm_russification_state_ok"
COMPLETE = "te_cm_russification_complete"
MARKER = "te_cm_russification_injected_fired"
THRESHOLD = "je_russification_state_russian_culture_min"
REGION_ITERATOR = "any_state_in_russia_western_borderlands"


def norm(value):
    """A parsed value as plain JSON: tuples become lists, so a ParadoxFileParser result
    and the committed snapshot (which holds the same parse as JSON) compare directly.
    Every (operator, value) pair stays, so a changed operator fails too."""
    return json.loads(json.dumps(value))


def dump(value):
    """A readable, order-sensitive rendering for assertEqual. Order matters: an effect
    block runs top to bottom."""
    return json.dumps(value, indent=1)


def parse_file(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(path), apply_directives=False)
    return {key: norm(value) for key, value in parser.data.items()}


def pairs(value):
    """The (operator, value) pairs a key holds: one pair, or a list of them when the key repeats."""
    if isinstance(value, list) and value and isinstance(value[0], list):
        return value
    return [value]


def body(pair):
    return pair[1]


def vanilla_entry():
    return body(norm(json.loads(VANILLA_JES.read_text(encoding="utf-8"))[ENTRY]))


def success_outcome(entry):
    """The one outcome of an entry that is a success (color gold_positive and no flags)."""
    found = [
        body(p) for p in pairs(entry["outcome"])
        if body(p).get("color", ["=", ""])[1].strip('"') == "gold_positive" and "flags" not in body(p)
    ]
    assert len(found) == 1, "expected one success outcome, found %d" % len(found)
    return found[0]


def injected_entry():
    parsed = parse_file(JE_FILE)
    assert list(parsed) == [INJECT_KEY], list(parsed)
    return body(parsed[INJECT_KEY])


def injected_outcome():
    entry = injected_entry()
    assert list(entry) == ["outcome"], list(entry)
    outcomes = pairs(entry["outcome"])
    assert len(outcomes) == 1, "the INJECT adds %d outcomes, not one" % len(outcomes)
    return body(outcomes[0])


def named_blocks(path, name):
    return body(parse_file(path)[name])


class TestInjectedOutcome(unittest.TestCase):
    def test_no_replace(self):
        """Vanilla content is changed by INJECT only (owner's preference: the smaller
        compatibility footprint)."""
        text = JE_FILE.read_text(encoding="utf-8-sig")
        self.assertIn(INJECT_KEY, text)
        self.assertNotIn("REPLACE:", text)

    def test_the_file_holds_one_inject_with_one_outcome_and_nothing_else(self):
        # injected_outcome() asserts the file's only key is the INJECT, whose only key is outcome.
        outcome = injected_outcome()
        # Vanilla's success outcome has no flags: a flag here would turn the copy hidden,
        # a timeout or an invalid outcome.
        self.assertNotIn("flags", outcome)

    def test_the_target_is_a_vanilla_entry_the_mod_does_not_define(self):
        self.assertIn(ENTRY, json.loads(VANILLA_JES.read_text(encoding="utf-8")))
        # No other mod file declares or replaces it (an INJECT on a REPLACEd or mod-only
        # entry is lost: mod_structure_audit).
        for path in sorted((ROOT / "common/journal_entries").glob("*.txt")):
            if path == JE_FILE:
                continue
            text = path.read_text(encoding="utf-8-sig")
            self.assertIsNone(
                re.search(r"(?m)^\s*(?:\w+:)?" + ENTRY + r"\s*=\s*\{", text), path.name
            )

    def test_outcome_mirrors_vanilla(self):
        """The injected outcome's effect is vanilla's success effect, apart from the
        added set_global_variable (the self-check's marker)."""
        injected = injected_outcome()
        vanilla = success_outcome(vanilla_entry())
        effect = copy.deepcopy(body(injected["effect"]))
        marker = effect.pop("set_global_variable", None)
        self.assertEqual(marker, ["=", MARKER])
        self.assertEqual(dump(effect), dump(body(vanilla["effect"])))

    def test_outcome_text_fields_mirror_vanilla(self):
        """Headers, color, conclusion and the effect descriptions are vanilla's, so the
        injected outcome needs no loc of its own."""
        injected = injected_outcome()
        vanilla = success_outcome(vanilla_entry())
        for key in ("header", "effect_header", "color", "conclusion_desc", "event_outcome_effect_desc"):
            self.assertIn(key, vanilla, key)
            self.assertEqual(dump(injected.get(key)), dump(vanilla[key]), key)
        # Nothing beyond vanilla's fields, bar the trigger and the effect.
        self.assertEqual(
            sorted(injected),
            sorted(set(vanilla)),
        )

    def test_trigger_is_the_scripted_trigger(self):
        injected = injected_outcome()
        self.assertEqual(injected["trigger"], ["=", {COMPLETE: ["=", "yes"]}])

    def test_effect_sets_the_marker_once(self):
        injected = injected_outcome()
        effect = body(injected["effect"])
        self.assertEqual(effect["set_global_variable"], ["=", MARKER])
        text = JE_FILE.read_text(encoding="utf-8-sig")
        self.assertEqual(len(re.findall(r"set_global_variable\s*=\s*" + MARKER + r"\b", text)), 1)

    def test_opener_carries_a_reviewed_note_naming_the_spec_section(self):
        """The audit that reads a REVIEWED note on an INJECT (mod_structure_audit) takes
        `# REVIEWED YYYY-MM-DD: rationale` on the INJECT line. It flags only a REPLACEd or
        mod-only target, which this is not, so the note is documentary."""
        text = JE_FILE.read_text(encoding="utf-8-sig")
        opener = [line for line in text.splitlines() if line.startswith(INJECT_KEY)]
        self.assertEqual(len(opener), 1)
        self.assertRegex(opener[0], r"^INJECT:je_russification = \{ # REVIEWED 2026-11-07: .*(?:section|§) ?7\b")

    def test_no_rule_gate(self):
        """counting cm_east_slavic is right with the rule on or off: pops already converted
        stay East Slavic, so the injected outcome needs no gate (and says so)."""
        text = JE_FILE.read_text(encoding="utf-8-sig")
        code = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
        self.assertNotIn("has_game_rule", code)
        self.assertNotIn("te_cm_system_enabled", code)
        self.assertRegex(text, r"(?i)#.*\bno (game )?rule gate\b")
        for name in (SHARE, STATE_OK, COMPLETE):
            self.assertNotIn("has_game_rule", dump(named_blocks_anywhere(name)), name)
            self.assertNotIn("te_cm_system_enabled", dump(named_blocks_anywhere(name)), name)

    def test_file_has_one_bom_and_tabs(self):
        raw = JE_FILE.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))
        for line in raw.decode("utf-8-sig").splitlines():
            self.assertFalse(line.startswith(" "), line)


def named_blocks_anywhere(name):
    for path in (VALUES, TRIGGERS):
        parsed = parse_file(path)
        if name in parsed:
            return body(parsed[name])
    raise AssertionError(name + " is defined in neither the values nor the triggers file")


class TestShare(unittest.TestCase):
    def test_counts_east_slavic(self):
        """The share names both Russian and the merged East Slavic culture."""
        text = dump(named_blocks_anywhere(SHARE))
        self.assertIn("cu:russian", text)
        self.assertIn("cu:cm_east_slavic", text)

    def test_share_sums_the_two_cultures_shares_in_vanillas_form(self):
        # The quoted culture_percent_state form is the one vanilla's own Russification value
        # uses in a script value (event_values.txt:321); population_by_culture has no vanilla use.
        block = named_blocks_anywhere(SHARE)
        self.assertEqual(block["value"], ["=", '"culture_percent_state(cu:russian)"'])
        self.assertEqual(block["add"], ["=", '"culture_percent_state(cu:cm_east_slavic)"'])
        self.assertEqual(list(block), ["value", "add"])

    def test_the_cultures_exist(self):
        self.assertIn("russian", json.loads(VANILLA_CULTURES.read_text(encoding="utf-8")))
        self.assertRegex(CULTURES.read_text(encoding="utf-8-sig"), r"(?m)^cm_east_slavic = \{")

    def test_the_share_sits_in_the_values_file(self):
        self.assertIn(SHARE, parse_file(VALUES))


class TestTriggers(unittest.TestCase):
    def test_state_ok_compares_the_share_with_vanillas_threshold(self):
        self.assertEqual(
            named_blocks_anywhere(STATE_OK),
            {SHARE: [">=", THRESHOLD]},
        )

    def test_the_threshold_is_a_vanilla_script_value(self):
        """je_russification_state_russian_culture_min is a script value in event_values.txt
        (not a define), global, so a mod trigger reads it in any scope."""
        vanilla = json.loads(VANILLA_VALUES.read_text(encoding="utf-8"))
        self.assertEqual(vanilla[THRESHOLD], ["=", "0.15"])

    def test_complete_is_vanillas_success_trigger_with_the_culture_test_widened(self):
        vanilla = copy.deepcopy(body(success_outcome(vanilla_entry())["trigger"]))
        region = body(vanilla[REGION_ITERATOR])
        self.assertIn("culture_percent_state", region)
        widened = {}
        for key, value in region.items():
            if key == "culture_percent_state":
                widened[STATE_OK] = ["=", "yes"]
            else:
                widened[key] = value
        vanilla[REGION_ITERATOR] = ["=", widened]
        self.assertEqual(dump(named_blocks_anywhere(COMPLETE)), dump(vanilla))

    def test_complete_reads_no_root_or_prev(self):
        """The success trigger is copied into a scripted trigger; it must not depend on a
        scope the call site gives (vanilla's reads none, which is why the copy is safe)."""
        text = dump(named_blocks_anywhere(COMPLETE))
        self.assertNotRegex(text, r"\b(ROOT|PREV|THIS)\b")

    def test_triggers_are_new_and_not_duplicated(self):
        text = TRIGGERS.read_text(encoding="utf-8-sig")
        for name in (STATE_OK, COMPLETE):
            self.assertEqual(len(re.findall(r"(?m)^" + name + r" = \{", text)), 1, name)


if __name__ == "__main__":
    unittest.main()
