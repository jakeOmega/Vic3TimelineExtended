"""The base game's Base Construction Capacity rule is cut to one setting that says it does nothing (#1768).

Vanilla's rule `free_construction` (`game/common/game_rules/00_game_rules.txt`) has three settings: Scaled (All),
with no flag; Scaled (Player Exemption), the default, flag `free_construction_scaled_player_exemption`; and
Maximum, flag `free_construction_unscaled`. None carries an `apply_modifier`. The engine reads the two flags to
scale the static modifier `country_gdp_construction` (+10 construction) to GDP, and the mod empties that modifier
(`REPLACE:country_gdp_construction = {}`), so no setting moves a country's construction. The one script reader is
vanilla's AI construction target, `ai_strategy_default`'s `wanted_construction_output`, which the mod's INJECT
sets to 0 (whether that replaces vanilla's field is #1771).

`common/game_rules` takes no REPLACE:, so `00_a_te_free_construction.txt` is a bare copy whose name sorts before
vanilla's file: the engine keeps a key's first bare definition in the folders probed
(`scripting_best_practices.md` § Load Order, facts 1-3). The one setting keeps the name of vanilla's default, so
the saves made under it keep their setting; `replace/` loc renames it No Effect and says where Base Construction
comes from.

Run: python3 -m pytest test_free_construction_rule.py
"""

import json
import os
import re
import subprocess
import unittest

from mod_state import split_loc_line
from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.path.join(REPO, "common", "game_rules")
RULE_FILE = "00_a_te_free_construction.txt"
VANILLA_RULES = os.path.join(REPO, "vanilla_parsed", "common", "game_rules.json")
MANIFEST = os.path.join(REPO, "vanilla_parsed", "manifest.json")
REPLACE_LOC_DIR = os.path.join(REPO, "localization", "english", "replace")
LOC_DIR = os.path.join(REPO, "localization", "english")
EXTRA_MODIFIERS = os.path.join(REPO, "common", "static_modifiers", "extra_modifiers.txt")

RULE = "free_construction"
KEPT = "free_construction_scaled_player_exemption"     # vanilla's default
DROPPED = ("free_construction_scaled_all", "free_construction_unscaled")


def _unwrap(node):
    """The parser's ('=', value) pair, or a list of them for a repeated key, as the last value."""
    if isinstance(node, list) and node and isinstance(node[0], (tuple, list)):
        node = node[-1]
    if isinstance(node, (tuple, list)) and len(node) == 2 and node[0] == "=":
        return node[1]
    return node


def _parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(path)
    return parser.data


def _loc(folder):
    out = {}
    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".yml"):
            with open(os.path.join(folder, fname), encoding="utf-8-sig") as f:
                for line in f:
                    parsed = split_loc_line(line)
                    if parsed:
                        out[parsed[0]] = parsed[1]
    return out


class FreeConstructionRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(VANILLA_RULES, encoding="utf-8") as f:
            cls.vanilla = json.load(f)
        with open(MANIFEST, encoding="utf-8") as f:
            cls.manifest = json.load(f)
        cls.mod = _parse(os.path.join(RULES_DIR, RULE_FILE))

    def test_the_mod_copy_has_one_setting_named_after_vanilla_s_default(self):
        self.assertEqual(list(self.mod), [RULE], f"{RULE_FILE} holds the one vanilla rule and nothing else")
        body = _unwrap(self.mod[RULE])
        self.assertEqual(_unwrap(body["default"]), KEPT)
        settings = [k for k in body if k != "default"]
        self.assertEqual(settings, [KEPT])
        setting = _unwrap(body[KEPT])
        self.assertEqual(_unwrap(setting["flag"]), KEPT,
                         "the setting keeps vanilla's flag, so vanilla's AI reader stays on the default's branch")
        self.assertNotIn("apply_modifier", setting)

    def test_vanilla_still_defines_the_rule_as_the_copy_assumes(self):
        """A vanilla patch that renames the rule, its default or its settings, or gives one an apply_modifier,
        fails here: the copy would then add a rule beside vanilla's, or drop what a setting now does."""
        self.assertIn(RULE, self.vanilla, "vanilla_parsed has no free_construction rule")
        body = _unwrap(self.vanilla[RULE])
        self.assertEqual(_unwrap(body["default"]), KEPT)
        self.assertEqual(sorted(k for k in body if k != "default"), sorted((KEPT,) + DROPPED))
        for setting in (KEPT,) + DROPPED:
            with self.subTest(setting=setting):
                self.assertNotIn("apply_modifier", _unwrap(body[setting]))
                flag = _unwrap(body[setting]).get("flag")
                self.assertIn(_unwrap(flag) if flag else None, (None, setting))

    def test_the_copy_sorts_before_vanilla_s_rule_files(self):
        """First bare definition wins, files in plain ASCII order with vanilla's and the mod's in one list."""
        vanilla_files = [os.path.basename(p) for p in self.manifest["sources"]
                         if p.startswith("game/common/game_rules/") and p.endswith(".txt")]
        self.assertTrue(vanilla_files, "the manifest lists no vanilla game_rules file")
        for name in vanilla_files:
            with self.subTest(vanilla=name):
                self.assertLess(RULE_FILE.encode(), name.encode())

    def test_no_other_mod_file_defines_the_rule(self):
        for fname in sorted(os.listdir(RULES_DIR)):
            if fname.endswith(".txt") and fname != RULE_FILE:
                with self.subTest(file=fname):
                    self.assertNotIn(RULE, _parse(os.path.join(RULES_DIR, fname)))

    def test_the_modifier_the_rule_scaled_stays_empty(self):
        """If the mod stopped emptying country_gdp_construction, vanilla's settings would mean something again."""
        with open(EXTRA_MODIFIERS, encoding="utf-8-sig") as f:
            text = f.read()
        self.assertRegex(text, r"(?m)^REPLACE:country_gdp_construction\s*=\s*\{\s*\}")

    def test_the_setting_says_it_does_nothing_and_names_the_rule_that_sets_base_construction(self):
        replace = _loc(REPLACE_LOC_DIR)
        self.assertEqual(replace.get(f"setting_{KEPT}"), "No Effect")
        desc = replace.get(f"setting_{KEPT}_desc", "")
        self.assertIn("Does nothing in Timeline Extended", desc)
        self.assertIn("$rule_free_market_construction_rule$", desc)
        self.assertIn("rule_free_market_construction_rule", _loc(LOC_DIR))
        ordinary = _loc(LOC_DIR)
        for key in (f"setting_{KEPT}", f"setting_{KEPT}_desc"):
            self.assertNotIn(key, ordinary, f"{key} belongs in replace/ only")

    def test_no_mod_script_reads_a_dropped_setting(self):
        """`has_game_rule` on a setting no file defines is silently false."""
        found = subprocess.run(
            ["git", "grep", "-n", "-E", "|".join(DROPPED), "--", "common", "events", "gui"],
            cwd=REPO, capture_output=True, text=True,
        ).stdout
        self.assertEqual([line for line in found.splitlines() if not re.search(r"\.txt:\d+:\s*#", line)], [])


if __name__ == "__main__":
    unittest.main()
