"""Which journal section each of the mod's journal entries sits in.

The mod has two journal entry groups of its own (common/journal_entry_groups/00_a_te_journal_entry_groups.txt):
Timeline Extended Systems, every entry the player works through with its own panel, tab, bar or buttons (the
owner's ask, which leaves out the narrative entries), and Rights and Society, the social debates (the
classification of that rule, PR #1797) and the Post-Scarcity Transition (the owner's placement). The rest keep a
vanilla group. A new entry has to be
placed on purpose, so this pins the members of each group and the entries left outside them.

- Every entry the mod defines or replaces names a group that exists (the engine says nothing about a missing one).
- The two groups hold exactly the entries listed here, the culture merges taken from their roster.
- The mod's bare entries outside the two groups are exactly the ones listed here.
- Each mod group is themed (a section of its own in the journal list), country-context, illustrated and named in
  English loc: no audit reads a group's name, and a missing one shows its key as the section's title.
- The group file sorts before vanilla's, so the mod's sections head the journal (database order).

Run: python3 -m pytest test_journal_entry_groups.py -q
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import culture_merges_config as cfg  # noqa: E402
from je_multiplier_scope_audit import parse_text  # noqa: E402
from paradox_file_parser import ParadoxFileParser  # noqa: E402

JE_DIR = ROOT / "common" / "journal_entries"
GROUP_DIR = ROOT / "common" / "journal_entry_groups"
VANILLA_GROUPS = ROOT / "vanilla_parsed" / "common" / "journal_entry_groups.json"
VANILLA_GROUP_FILE = "00_journal_entries.txt"
LOC_DIR = ROOT / "localization" / "english"

SYSTEMS = "je_group_te_systems"
RIGHTS = "je_group_te_rights_and_society"

SYSTEM_ENTRIES = frozenset({
    "je_banking_cycle",
    "je_tax_code",
    "je_strategic_reserve",
    "je_global_warming",
    "je_world_climate",
    "je_space_race_suborbital",
    "je_space_race_orbital",
    "je_space_race_moon_landing",
    "je_space_race_probe",
    "je_space_race_mars_landing",
    "je_space_race_interstellar_probe",
    "je_space_race_interstellar_results",
    "je_space_race_solar_colonization",
    "je_nuclear_program",
    "je_united_nations",
    "je_covert_warfare",
    "je_cultural_hegemony",
    "je_colonial_empire",
    "je_grand_monuments",
    "je_heir_education",
})
RIGHTS_ENTRIES = frozenset({
    "je_civil_rights",
    "je_digital_rights",
    "je_human_augmentation",
    "je_morphological_freedom",
    "je_mental_health_crisis",
    "je_post_scarcity",  # the owner: "I'd put it in society"
})
# The mod's own entries that stay in a vanilla group: The Gathering Storm, State Collapse and Create New Religion,
# and the Map Room, which is contextless and listed in no journal.
OUTSIDE = frozenset({"je_world_war", "je_state_collapse", "je_create_new_religion", "je_te_map_room"})


def merge_entries() -> frozenset[str]:
    return frozenset("je_te_cm_%s" % merge.key for merge in cfg.MERGES)


def parse(path: Path):
    return parse_text(path.read_text(encoding="utf-8-sig"), path.relative_to(ROOT).as_posix())[0]


def field(node, key: str) -> str | None:
    return next((c.value for c in node.children if c.key == key), None)


def mod_entries() -> dict[str, tuple[str, str | None]]:
    """Entry key (directive kept) -> (file, its group or None)."""
    found: dict[str, tuple[str, str | None]] = {}
    for path in sorted(JE_DIR.glob("*.txt")):
        for node in parse(path):
            if node.children:
                found[node.key] = (path.name, field(node, "group"))
    return found


def mod_groups() -> dict[str, tuple[str, dict[str, str]]]:
    """Group key -> (file, its fields). The full parser, which keeps a quoted path whole."""
    groups: dict[str, tuple[str, dict[str, str]]] = {}
    for path in sorted(GROUP_DIR.glob("*.txt")):
        parser = ParadoxFileParser()
        parser.parse_file(str(path), apply_directives=False)
        for key, (_, body) in parser.data.items():
            groups[key] = (path.name, {name: value for name, (_, value) in body.items()})
    return groups


def vanilla_group_names() -> set[str]:
    return set(json.loads(VANILLA_GROUPS.read_text(encoding="utf-8")))


def english_loc_keys() -> set[str]:
    keys: set[str] = set()
    for path in LOC_DIR.rglob("*.yml"):
        keys.update(re.findall(r"^\s*([\w.\-]+):\d*\s*\"", path.read_text(encoding="utf-8-sig"), re.M))
    return keys


class JournalEntryGroupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = mod_entries()
        cls.groups = mod_groups()
        cls.bare = {key: group for key, (_, group) in cls.entries.items() if ":" not in key}

    def test_every_entry_names_a_group_that_exists(self):
        known = vanilla_group_names() | set(self.groups)
        for key, (path, group) in self.entries.items():
            if key.startswith(("INJECT:", "TRY_INJECT:")) and group is None:
                continue  # an injection keeps the vanilla entry's group
            with self.subTest(entry=key, file=path):
                self.assertIsNotNone(group, "names no group")
                self.assertIn(group, known, "names a group nothing defines")

    def test_systems_group_holds_exactly_the_systems(self):
        members = {key for key, group in self.bare.items() if group == SYSTEMS}
        expected = SYSTEM_ENTRIES | merge_entries()
        self.assertEqual(sorted(members - expected), [], "in Timeline Extended Systems but not listed here")
        self.assertEqual(sorted(expected - members), [], "listed here but not in Timeline Extended Systems")

    def test_rights_group_holds_exactly_the_debates(self):
        members = {key for key, group in self.bare.items() if group == RIGHTS}
        self.assertEqual(members, set(RIGHTS_ENTRIES))

    def test_only_the_listed_entries_stay_outside(self):
        outside = {key for key, group in self.bare.items() if group not in (SYSTEMS, RIGHTS)}
        self.assertEqual(outside, set(OUTSIDE),
                         "a new entry goes in one of the two groups, or in OUTSIDE with the reason")

    def test_vanilla_entries_keep_their_groups(self):
        for key, (path, group) in self.entries.items():
            if ":" in key and group is not None:
                with self.subTest(entry=key, file=path):
                    self.assertNotIn(group, (SYSTEMS, RIGHTS))

    def test_the_mod_groups_are_sections(self):
        self.assertEqual(set(self.groups), {SYSTEMS, RIGHTS})
        loc = english_loc_keys()
        for key, (path, fields) in self.groups.items():
            with self.subTest(group=key):
                self.assertEqual(fields.get("themed"), "yes", "only a themed group is a section of the journal")
                self.assertEqual(fields.get("context"), "country", "the members' default context")
                self.assertRegex(fields.get("illustration", ""), r'^"gfx/interface/illustrations/journal/\w+\.dds"$')
                self.assertIn(key, loc, "the section's title")

    def test_the_mod_sections_load_before_vanilla_groups(self):
        for key, (path, _) in self.groups.items():
            with self.subTest(group=key):
                self.assertLess(path.encode(), VANILLA_GROUP_FILE.encode())

    def test_counts(self):
        self.assertEqual(len(SYSTEM_ENTRIES | merge_entries()), len(SYSTEM_ENTRIES) + len(cfg.MERGES))
        self.assertEqual((len(SYSTEM_ENTRIES), len(RIGHTS_ENTRIES), len(OUTSIDE)), (20, 6, 4))


if __name__ == "__main__":
    unittest.main()
