"""Protected Class opens Grant Leadership and the two Grant Command interactions to women.

te_vanilla_women_in_office.txt restates the three vanilla character interactions
whole (REPLACE:, since an INJECT can't add to `possible`) with one MOD line in each
`possible`, and one ruler guard in Grant Leadership's AI weight. Once those come
out, each entry must equal vanilla's (vanilla_parsed): a vanilla patch that moves
one fails here, and the copy is rebuilt from the new text."""

import copy
import json
import unittest
from pathlib import Path

from test_tax_code_rule import load, plain

ROOT = Path(__file__).resolve().parent
PATH = "common/character_interactions/te_vanilla_women_in_office.txt"
VANILLA = "vanilla_parsed/common/character_interactions.json"
VANILLA_LAWS = "vanilla_parsed/common/laws.json"
MOD_LAWS = "common/laws/extra_laws.txt"
SUFFRAGE = {"has_law_or_variant": "law_type:law_womens_suffrage"}
PROTECTED_CLASS = {"has_law": "law_type:law_protected_class"}
# The country each interaction reads its laws from.
COUNTRY = {
    "grant_command_to_ruler": "owner",
    "grant_leadership_to_agitator": "scope:actor",
    "grant_command_to_agitator": "owner",
}
RULER_READ = {"this.ideology": "owner.ruler.ideology"}
RULER_GUARD = {"exists": "owner.ruler",
               "trigger_if": {"limit": {"exists": "owner.ruler"}, **RULER_READ}}


class WomenInOfficeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(ROOT / VANILLA, encoding="utf-8") as f:
            cls.vanilla = plain(json.load(f))
        cls.mod = load(PATH)
        raw = (ROOT / PATH).read_bytes()
        cls.bom = raw.startswith(b"\xef\xbb\xbf") and not raw.startswith(b"\xef\xbb\xbf" * 2)

    def entry(self, name):
        return copy.deepcopy(self.mod[f"REPLACE:{name}"])

    def test_file_holds_the_three_replaces_and_one_bom(self):
        self.assertEqual(set(self.mod), {f"REPLACE:{name}" for name in COUNTRY})
        self.assertTrue(self.bom)

    def test_each_possible_accepts_protected_class_beside_suffrage(self):
        for name, country in COUNTRY.items():
            with self.subTest(name=name):
                gate = self.entry(name)["possible"]["OR"]
                self.assertEqual(gate["is_female"], "no")
                self.assertEqual(gate[country], [SUFFRAGE, PROTECTED_CLASS])

    def test_each_entry_is_vanilla_but_for_the_mod_lines(self):
        for name, country in COUNTRY.items():
            with self.subTest(name=name):
                mine = self.entry(name)
                gate = mine["possible"]["OR"]
                gate[country] = gate[country][0]
                if name == "grant_leadership_to_agitator":
                    weights = mine["ai_chance"]["if"]
                    guarded = [w for w in weights if w["limit"] == RULER_GUARD]
                    self.assertEqual(len(guarded), 1)
                    guarded[0]["limit"] = dict(RULER_READ)
                self.assertEqual(mine, self.vanilla[name])

    def test_protected_class_is_not_a_suffrage_variant(self):
        """has_law_or_variant on suffrage misses Protected Class: both sit in one law group."""
        laws = load(MOD_LAWS)
        protected = laws["law_protected_class"]
        self.assertEqual(protected["group"], "lawgroup_rights_of_women")
        self.assertNotIn("parent", protected)
        with open(ROOT / VANILLA_LAWS, encoding="utf-8") as f:
            vanilla_laws = plain(json.load(f))
        self.assertEqual(vanilla_laws["law_womens_suffrage"]["group"], "lawgroup_rights_of_women")


if __name__ == "__main__":
    unittest.main()
