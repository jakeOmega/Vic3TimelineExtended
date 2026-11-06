"""`remove_all_ideologies` must name every interest-group ideology (#1406).

The custom-religion button strips the Devout interest group's ideologies with
it before adding the ones the player picked. An ideology the list leaves out
stays on the group with no log line: the effect missed about thirty of
vanilla's, plus the mod's own, until #1406 (the 1.15 migration had added only
1.15's thirteen new ones).

An interest-group ideology here is any ideology, vanilla's (the committed
`vanilla_parsed/` snapshot) or the mod's (`common/ideologies/`), that is
neither a character ideology (`character_ideology = yes`) nor a political
movement's (`ideology_*_movement`, `_movement_<n>`; vanilla never adds one to
an interest group). The list must also name nothing else, so a removed or
renamed ideology shows up here too.
"""
from __future__ import annotations

import glob
import json
import os
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
_MOVEMENT_RE = re.compile(r"_movement(_[a-z0-9]+)?$")
_PREFIX_RE = re.compile(r"^(?:REPLACE|INJECT|TRY_INJECT|TRY_REPLACE|REPLACE_OR_CREATE|INJECT_OR_CREATE):")


def _body(value):
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def _is_character(body) -> bool:
    return isinstance(body, dict) and _body(body.get("character_ideology")) == "yes"


def _parse(path: str) -> dict:
    parser = ParadoxFileParser()
    parser.parse_file(path)
    return parser.data


def interest_group_ideologies() -> set[str]:
    with open(os.path.join(REPO, "vanilla_parsed", "common", "ideologies.json"), encoding="utf-8") as fh:
        vanilla = json.load(fh)
    found = {name for name, value in vanilla.items() if not _is_character(_body(value))}
    character = {name for name, value in vanilla.items() if _is_character(_body(value))}
    for path in sorted(glob.glob(os.path.join(REPO, "common", "ideologies", "*.txt"))):
        for key, value in _parse(path).items():
            name = _PREFIX_RE.sub("", key)
            if key != name and name in vanilla:
                continue  # an edit of a vanilla ideology, classified above
            (character if _is_character(_body(value)) else found).add(name)
    return {name for name in found - character if not _MOVEMENT_RE.search(name)}


def removed_ideologies() -> list[str]:
    effects = _parse(os.path.join(REPO, "common", "scripted_effects", "extra_effects.txt"))
    body = _body(effects["remove_all_ideologies"])
    entries = body["remove_ideology"]
    entries = entries if isinstance(entries, list) else [entries]
    return [_body(entry) for entry in entries]


class RemoveAllIdeologiesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = interest_group_ideologies()
        cls.removed = removed_ideologies()

    def test_every_interest_group_ideology_is_removed(self):
        missing = sorted(self.expected - set(self.removed))
        self.assertEqual(missing, [], "add these to remove_all_ideologies (extra_effects.txt)")

    def test_nothing_else_is_named(self):
        extra = sorted(set(self.removed) - self.expected)
        self.assertEqual(extra, [], "not an interest-group ideology: a character or movement "
                                    "ideology, or one that no longer exists")

    def test_no_ideology_is_named_twice(self):
        twice = sorted({name for name in self.removed if self.removed.count(name) > 1})
        self.assertEqual(twice, [])

    def test_the_classification_finds_both_sources(self):
        # Guards the filter itself: one of vanilla's, one of 1.15's, one of the mod's.
        for name in ("ideology_paternalistic", "ideology_autocratic", "ideology_multicultural_ig"):
            self.assertIn(name, self.expected)
        for name in ("ideology_orleanist", "ideology_labor_movement", "ideology_modernizer_movement_1"):
            self.assertNotIn(name, self.expected)


if __name__ == "__main__":
    unittest.main()
