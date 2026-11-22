"""Every `has_game_rule` in the mod's script names a setting some rule defines.

A `has_game_rule` naming a setting no file defines is true, not false: read in game on 2026-11-13 (harness run
20261114T014601Z, #1768), where `has_game_rule = free_construction_unscaled` (a vanilla setting the mod's copy of
the rule no longer defines) and a made-up name both passed in a setup's `limit`, while a defined setting the game
wasn't on did not. The engine logs `Invalid database object` where the trigger is parsed, and nothing else
(`scripting_best_practices.md` § "`has_game_rule` on a Setting No File Defines Is True"). So a setting removed or
renamed, or a typo, turns its checks on everywhere.

The settings are vanilla's (`vanilla_parsed/common/game_rules.json`) and the mod's (`common/game_rules/`), a mod rule
of a vanilla rule's name replacing vanilla's settings, as `00_a_te_free_construction.txt` does (the engine keeps the
first bare definition, and that file sorts first: `test_free_construction_rule.py`).

Run: python3 -m pytest test_has_game_rule_targets.py
"""

import json
import os
import re
import subprocess
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.path.join(REPO, "common", "game_rules")
VANILLA_RULES = os.path.join(REPO, "vanilla_parsed", "common", "game_rules.json")
READ = re.compile(r"has_game_rule\s*=\s*([A-Za-z0-9_]+)")


def _body(node):
    """A rule's block from the parser's ('=', block) pair (a list of them for a repeated key) or the snapshot's
    ["=", block]."""
    if isinstance(node, list) and node and isinstance(node[0], (tuple, list)):
        node = node[-1]
    if isinstance(node, (tuple, list)) and len(node) == 2 and node[0] == "=":
        return node[1]
    return node


def defined_settings():
    """{rule: [setting, ...]} as the game loads them: vanilla's rules, each mod rule replacing one of its name."""
    with open(VANILLA_RULES, encoding="utf-8") as f:
        rules = {rule: [k for k in _body(b) if k != "default"] for rule, b in json.load(f).items()}
    for fname in sorted(os.listdir(RULES_DIR)):
        if fname.endswith(".txt"):
            parser = ParadoxFileParser()
            parser.parse_file(os.path.join(RULES_DIR, fname))
            for rule, b in parser.data.items():
                body = _body(b)
                if isinstance(body, dict):
                    rules[rule] = [k for k in body if k != "default"]
    return rules


def mod_reads():
    """[(path:line, setting)] for every `has_game_rule = X` outside a comment in the mod's script and GUI."""
    out = subprocess.run(
        ["git", "grep", "-n", "-E", r"has_game_rule\s*=", "--", "common", "events", "gui"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout
    reads = []
    for line in out.splitlines():
        path, number, text = line.split(":", 2)
        code = text.split("#", 1)[0]
        for found in READ.finditer(code):
            reads.append((f"{path}:{number}", found.group(1)))
    return reads


class HasGameRuleTargetTests(unittest.TestCase):
    def test_every_read_names_a_defined_setting(self):
        settings = {s for names in defined_settings().values() for s in names}
        reads = mod_reads()
        self.assertGreater(len(reads), 200, "the scan found too few has_game_rule reads")
        undefined = [f"{where}: {name}" for where, name in reads if name not in settings]
        self.assertEqual(undefined, [], "has_game_rule on a setting no rule defines is true in game")

    def test_the_dropped_vanilla_settings_are_not_defined(self):
        # The control: the mod's copy of free_construction keeps one of vanilla's three settings.
        settings = {s for names in defined_settings().values() for s in names}
        self.assertIn("free_construction_scaled_player_exemption", settings)
        self.assertNotIn("free_construction_unscaled", settings)
        self.assertNotIn("free_construction_scaled_all", settings)
        self.assertIn("allow_monument_effects", settings)


if __name__ == "__main__":
    unittest.main()
