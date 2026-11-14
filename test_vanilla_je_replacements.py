"""The vanilla journal entries the mod restates whole (REPLACE:) outside the tax code.

te_vanilla_opium.txt closes The Opium Trade at the International Opium Convention;
te_vanilla_turtle_island.txt keeps The Nations of Turtle Island off North American
unions; te_vanilla_war_nursing.txt lets War Wounded count Medevac Helicopters. Each
is vanilla's entry (vanilla_parsed, 1.15) plus lines marked MOD, so once those come
out (or, where a MOD line edits one of vanilla's, vanilla's line goes back) the entry
must equal vanilla's: a vanilla patch that moves the entry fails here, and the copy
is rebuilt from the new text (the tax code's three have the same test,
test_tax_code_bypass.VanillaJournalEntryTest)."""

import copy
import json
import re
import unittest
from pathlib import Path

from je_test_helpers import outcome, outcomes, parsed_kind
from test_tax_code_rule import load, plain

ROOT = Path(__file__).resolve().parent
OPIUM = "common/journal_entries/te_vanilla_opium.txt"
TURTLE = "common/journal_entries/te_vanilla_turtle_island.txt"
WAR_NURSING = "common/journal_entries/te_vanilla_war_nursing.txt"
VANILLA_JES = "vanilla_parsed/common/journal_entries.json"
UNION = {"te_is_north_american_capable_union": "yes"}
FIRST_AID = "mobilization_option:mobilization_option_first_aid"
FIELD_HOSPITALS = "mobilization_option:mobilization_option_field_hospitals"


def remove(block, key, value):
    """`block` without one `key = value` line; a key left with one value is no longer a list."""
    values = block[key] if isinstance(block[key], list) else [block[key]]
    left = [v for v in values if v != value]
    if len(left) != len(values) - 1:
        raise AssertionError(f"{key} = {value} found {len(values) - len(left)} times")
    if not left:
        del block[key]
    else:
        block[key] = left if len(left) > 1 else left[0]


def drop_outcome(entry, kind):
    """`entry` without its one outcome of `kind`, which it returns."""
    found = [o for o in outcomes(entry) if parsed_kind(o) == kind]
    if len(found) != 1:
        raise AssertionError(f"{len(found)} {kind} outcomes")
    left = [o for o in outcomes(entry) if o is not found[0]]
    if not left:
        del entry["outcome"]
    else:
        entry["outcome"] = left if len(left) > 1 else left[0]
    return found[0]


class ReplacementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(ROOT / VANILLA_JES, encoding="utf-8") as f:
            cls.vanilla = plain(json.load(f))

    def entry(self, path, name):
        mod = load(path)
        self.assertEqual(set(mod), {f"REPLACE:{name}"})
        self.assertTrue((ROOT / path).read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertFalse((ROOT / path).read_bytes().startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))
        return copy.deepcopy(mod[f"REPLACE:{name}"])

    def test_opium_is_vanilla_but_for_the_convention(self):
        mine = self.entry(OPIUM, "je_opium")
        fail = drop_outcome(mine, "fail")
        self.assertEqual(fail["trigger"], {"custom_tooltip": {
            "text": "je_opium_international_opium_convention_tt", "game_date": "1912.1.23"}})
        self.assertEqual(fail["effect"]["set_variable"], {"name": "opium_je_done"})
        for gate in ("is_shown_when_inactive", "possible"):
            remove(mine[gate], "game_date", "1912.1.23")
        self.assertEqual(mine, self.vanilla["je_opium"])
        # vanilla's own success outcome sets the same marker
        self.assertEqual(outcome(self.vanilla["je_opium"], "complete")["effect"]["set_variable"],
                         {"name": "opium_je_done"})

    def test_the_convention_dates_are_one_date(self):
        text = (ROOT / OPIUM).read_text(encoding="utf-8-sig")
        self.assertEqual(sorted(set(re.findall(r"game_date\s*([<>]=?)\s*(\S+)", text))),
                         [("<", "1912.1.23"), (">=", "1912.1.23")])
        self.assertEqual(len(re.findall(r"game_date < 1912\.1\.23 # MOD", text)), 2)

    def test_turtle_island_is_vanilla_but_for_the_unions(self):
        mine = self.entry(TURTLE, "je_unite_the_nations")
        invalid = drop_outcome(mine, "invalid")
        self.assertEqual(invalid["trigger"], UNION)
        for gate in ("is_shown_in_lobby", "is_shown_when_inactive"):
            remove(mine[gate], "NOT", UNION)
        self.assertEqual(mine, self.vanilla["je_unite_the_nations"])

    def test_war_wounded_is_vanilla_but_for_the_medical_options(self):
        """Three of vanilla's tests read the medical triggers, and one block is added.

        Each MOD line is swapped back for the vanilla text it stands in for, written
        out here, so a vanilla patch to those lines fails the comparison too."""
        mine = self.entry(WAR_NURSING, "je_war_nursing")

        def formation(block):
            """The general test under a country-scope block, or under a war-scope one."""
            general = block["any_scope_front"]["any_scope_general"] if "any_scope_front" in block \
                else block["any_scope_war"]["any_scope_front"]["any_scope_general"]
            self.assertEqual(general["owner"], "ROOT")
            return general

        start = formation(mine["possible"])
        self.assertEqual(start["this.commander_military_formation"], {"te_formation_has_medic_support": "no"})
        start["this.commander_military_formation"] = {
            "NOR": {"has_mobilization_option": [FIRST_AID, FIELD_HOSPITALS]}}

        done = outcome(mine, "complete")
        self.assertEqual(done["trigger"].pop("te_army_has_field_hospitals_or_better_share"), "yes")
        done["trigger"] = {
            "army_mobilization_option_fraction": {"target": FIELD_HOSPITALS, "value": "0.2"},
            **done["trigger"]}
        general = formation(done["trigger"])
        self.assertEqual(general["this.commander_military_formation"],
                         {"te_formation_has_field_hospitals_or_better": "yes"})
        general["this.commander_military_formation"] = {"has_mobilization_option": FIELD_HOSPITALS}

        saved = done["effect"].pop("hidden_effect")
        war = saved["random_scope_war"]
        self.assertEqual(formation(war["limit"])["this.commander_military_formation"],
                         {"te_formation_has_field_hospitals_or_better": "yes"})
        self.assertEqual(war["save_scope_as"], "complete_nursing_war")
        self.assertEqual(war["random_scope_front"],
                         {"random_scope_state": {"save_scope_as": "ongoing_war_state"}})

        self.assertEqual(mine, self.vanilla["je_war_nursing"])

    def test_war_wounded_saves_its_scopes_before_the_event(self):
        """nursing_events.4 reads the scopes the outcome saves, so the save comes first."""
        text = (ROOT / WAR_NURSING).read_text(encoding="utf-8-sig")
        self.assertLess(text.index("save_scope_as = complete_nursing_war"),
                        text.index("trigger_event = { id = nursing_events.4 }"))


if __name__ == "__main__":
    unittest.main()
