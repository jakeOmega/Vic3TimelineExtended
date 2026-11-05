# -*- coding: utf-8 -*-
"""Every literal `type =` a diplomatic-pact trigger or effect names is a diplomatic action.

has_diplomatic_pact, create_diplomatic_pact and remove_diplomatic_pact look `type` up among the
diplomatic actions (`common/diplomatic_actions/`). Since Sphere of Influence an alliance and a
defensive pact are treaty articles, not actions, so `type = alliance` fails the engine's load-time
check (`has_diplomatic_pact trigger [ type: Not found in database class
CDiplomaticActionTypeDataBase ]`) and the trigger never matches. Ask about an alliance with vanilla's
`has_treaty_alliance_with = { TARGET = ... }`. Slice 6a's marines shipped the old form (found in the
2026-10-26 log triage). scripting_best_practices.md, the `has_diplomatic_pact = { type = alliance }`
bullet.

Run: python3 -m unittest test_diplomatic_pact_types -v
"""

import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
SCANNED = ("common", "events")
OPENER = re.compile(r"\b(?:has|create|remove)_diplomatic_pact\s*=\s*\{")
TYPE = re.compile(r"(?<![\w.:$])type\s*=\s*([\w$:.]+)")
TOP_KEY = re.compile(r"^(?:(?:INJECT|REPLACE|TRY_INJECT|TRY_REPLACE|REPLACE_OR_CREATE|INJECT_OR_CREATE):)?([A-Za-z_][\w]*)\s*=\s*\{", re.M)


def _scripts():
    for top in SCANNED:
        for root, _, names in os.walk(os.path.join(REPO, top)):
            for name in sorted(names):
                if name.endswith(".txt"):
                    yield os.path.join(root, name)


def _code(path):
    """The file's text with comments blanked out (line numbers kept)."""
    with open(path, encoding="utf-8-sig") as f:
        return "".join(line.rstrip("\n").split("#", 1)[0] + "\n" for line in f)


def pact_types(text):
    """(line, type) for each literal `type` at the top level of a pact trigger's or effect's block.

    A `$PARAM$`-built name (`un_lobby_$KIND$`) or a scope (`scope:x`) is skipped.
    """
    found = []
    for match in OPENER.finditer(text):
        depth, start = 1, match.end()
        for end in range(start, len(text)):
            if text[end] == "{":
                depth += 1
            elif text[end] == "}":
                depth -= 1
                if depth == 0:
                    break
        else:
            continue
        body = text[start:end]
        flat = re.sub(r"\{[^{}]*\}", lambda m: " " * len(m.group()), body)
        while "{" in flat:
            flat = re.sub(r"\{[^{}]*\}", lambda m: " " * len(m.group()), flat)
        for t in TYPE.finditer(flat):
            if "$" in t.group(1) or ":" in t.group(1):
                continue
            found.append((text.count("\n", 0, start + t.start()) + 1, t.group(1)))
    return found


def diplomatic_actions():
    with open(os.path.join(REPO, "vanilla_parsed", "common", "diplomatic_actions.json"), encoding="utf-8") as f:
        keys = set(json.load(f))
    for root, _, names in os.walk(os.path.join(REPO, "common", "diplomatic_actions")):
        for name in names:
            if name.endswith(".txt"):
                keys |= set(TOP_KEY.findall(_code(os.path.join(root, name))))
    return keys


class DiplomaticPactTypeTests(unittest.TestCase):
    def test_the_scan_reads_types_and_only_literal_ones(self):
        text = (
            "a = { has_diplomatic_pact = { who = ROOT type = rivalry } }\n"
            "b = { create_diplomatic_pact = {\n\tcountry = scope:x\n\ttype = $ACTION$\n} }\n"
            "c = { has_diplomatic_pact = { who = scope:y type = alliance is_initiator = yes } }\n"
            "d = { remove_diplomatic_pact = { country = scope:z type = scope:t } }\n"
            "f = { has_diplomatic_pact = { who = scope:z type = un_lobby_$KIND$ } }\n"
            "e = { has_diplomatic_pact = { who = scope:x type = embargo limit = { type = nested } } }\n"
        )
        self.assertEqual(pact_types(text), [(1, "rivalry"), (6, "alliance"), (9, "embargo")])

    def test_the_rosters_are_read(self):
        """A path error would pass the last test with nothing scanned."""
        actions = diplomatic_actions()
        self.assertIn("rivalry", actions)
        self.assertNotIn("alliance", actions)
        found = sum(len(pact_types(_code(path))) for path in _scripts())
        self.assertGreater(found, 50)

    def test_every_pact_type_is_a_diplomatic_action(self):
        actions = diplomatic_actions()
        bad = [f"{os.path.relpath(path, REPO)}:{line}: type = {name}"
               for path in _scripts() for line, name in pact_types(_code(path)) if name not in actions]
        self.assertEqual(bad, [], "an alliance or defensive pact is a treaty article: use has_treaty_alliance_with"
                                  " / has_treaty_defensive_pact_with = { TARGET = ... }")


if __name__ == "__main__":
    unittest.main()
