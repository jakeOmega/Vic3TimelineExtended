"""The homeland unlock list names exactly the sources of the unlock modifier.

TE_HOMELAND_UNLOCK_SOURCES tells a player whose homelands are locked which
laws, power bloc principle tiers and technology enable homeland changes. It
is hand-written loc, so this test finds every block in common/ that grants
country_homelands_can_change_bool and fails when the list misses a source or
names one that no longer grants it.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMON = ROOT / "common"
LOC = ROOT / "localization/english/te_miscellaneous_l_english.yml"
PRINCIPLE_GROUPS = COMMON / "power_bloc_principle_groups"

MODIFIER = "country_homelands_can_change_bool"
# `modifier:X = yes` in a trigger reads the modifier; it does not grant it.
GRANT = re.compile(r"(?<![\w:.])" + MODIFIER + r"\s*=\s*yes\b")
OPENER = re.compile(r"^([A-Za-z_][\w:.]*)\s*=\s*\{")
ROMAN = ["I", "II", "III", "IV", "V", "VI"]
# The kinds of source the loc list has a line for.
LISTED_KINDS = {"laws", "power_bloc_principles", "technology"}


def grant_sites():
    """{(common/ subdirectory, top-level entity id)} for every grant."""
    sites = set()
    for path in sorted(COMMON.rglob("*.txt")):
        text = path.read_text(encoding="utf-8-sig")
        if MODIFIER not in text:
            continue
        kind = path.relative_to(COMMON).parts[0]
        depth, entity = 0, None
        for line in text.splitlines():
            code = line.split("#", 1)[0]
            if depth == 0:
                match = OPENER.match(code.strip())
                if match:
                    # REPLACE:law_ethnostate / INJECT:x name the entity x.
                    entity = match.group(1).split(":")[-1]
            if depth > 0 and GRANT.search(code):
                sites.add((kind, entity))
            depth += code.count("{") - code.count("}")
    return sites


def principle_levels():
    """{principle group: [principle ids, lowest tier first]} for mod groups."""
    levels = {}
    for path in sorted(PRINCIPLE_GROUPS.glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig")
        for match in re.finditer(
                r"^(principle_group_\w+)\s*=\s*\{.*?\blevels\s*=\s*\{([^}]*)\}",
                text, re.M | re.S):
            levels[match.group(1)] = match.group(2).split()
    return levels


def loc_value(key):
    text = LOC.read_text(encoding="utf-8-sig")
    match = re.search(r'^ ' + key + r':\d* "(.*)"\s*$', text, re.M)
    if not match:
        raise AssertionError(f"{key} missing from {LOC.name}")
    return match.group(1)


class HomelandUnlockSourcesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sites = grant_sites()
        cls.text = loc_value("TE_HOMELAND_UNLOCK_SOURCES")

    def granted(self, kind):
        return {entity for k, entity in self.sites if k == kind}

    def test_finds_grants(self):
        # Guards the scan itself: an empty result would pass every check.
        self.assertTrue(self.granted("laws"))
        self.assertTrue(self.granted("technology"))

    def test_every_source_is_a_listed_kind(self):
        unlisted = sorted(s for s in self.sites if s[0] not in LISTED_KINDS)
        self.assertEqual(
            unlisted, [],
            f"{MODIFIER} is granted from a kind of source that "
            "TE_HOMELAND_UNLOCK_SOURCES has no line for; add one")

    def test_laws_match(self):
        listed = set(re.findall(r"GetLawType\('(\w+)'\)", self.text))
        self.assertEqual(listed, self.granted("laws"))

    def test_technologies_match(self):
        listed = set(re.findall(r"GetTechnology\('(\w+)'\)", self.text))
        self.assertEqual(listed, self.granted("technology"))

    def test_principle_tiers_match(self):
        groups = principle_levels()
        granted = self.granted("power_bloc_principles")
        expected = {}
        for group, levels in groups.items():
            tiers = [i for i, p in enumerate(levels) if p in granted]
            if not tiers:
                continue
            first = tiers[0]
            # "tier N or higher" is only true if every higher tier grants too.
            self.assertEqual(
                tiers, list(range(first, len(levels))),
                f"{group}: granting tiers are not tier {ROMAN[first]} and up")
            expected[group] = ROMAN[first]
        in_groups = {p for levels in groups.values() for p in levels}
        self.assertEqual(sorted(granted - in_groups), [],
                         "granting principle not in any mod principle group")

        listed = dict(re.findall(
            r"GetPowerBlocPrincipleGroup\('(\w+)'\)\.GetName\] tier (\w+) or higher",
            self.text))
        self.assertEqual(listed, expected)


if __name__ == "__main__":
    unittest.main()
