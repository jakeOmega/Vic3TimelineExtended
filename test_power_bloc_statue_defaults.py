"""Every power bloc identity the mod defines is a default for a statue hero and a pedestal (issue #1916).

Vanilla's statue pieces (gfx/map/power_block_statues/heroes/00_heroes.txt, pedestals/00_pedestals.txt) list the
identities each is a default for, and name only vanilla's six. The engine logs "Identity '<id>' is not default for any
hero!" (and pedestal) at load for any identity no piece lists, and the AI's random statue has nothing to draw for it.
The mod's two files INJECT its identities into the default lists of the pieces of each one's nearest vanilla identity.
A new mod identity must be added there too.
"""

import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IDENTITIES_DIR = ROOT / "common" / "power_bloc_identities"
STATUES = ROOT / "gfx" / "map" / "power_block_statues"
HEROES = STATUES / "heroes" / "te_statue_hero_defaults.txt"
PEDESTALS = STATUES / "pedestals" / "te_statue_pedestal_defaults.txt"

# The pieces of each vanilla identity (vanilla 1.15.2's default_choice_for_identities lists), and the identity each
# mod identity takes them from (owner, 2026-11-19: the nearest vanilla equivalent).
VANILLA_HEROES = {
    "identity_trade_league": {"hero_globe", "hero_octopus"},
    "identity_cultural": {"hero_armillary", "hero_dancinglady", "hero_globe"},
    "identity_military_treaty_organization": {"hero_pointingman", "hero_prancinghorse"},
}
VANILLA_PEDESTALS = {
    "identity_trade_league": {"pedestal_01", "pedestal_02"},
    "identity_cultural": {"pedestal_06"},
    "identity_military_treaty_organization": {"pedestal_03", "pedestal_04"},
}
NEAREST = {
    "identity_creditors_consortium": "identity_trade_league",
    "identity_research_commons": "identity_cultural",
    "identity_diplomatic": "identity_military_treaty_organization",
}


def strip_comments(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def mod_identities():
    """Identities the mod defines bare (an INJECT into a vanilla identity is not a new one)."""
    names = set()
    for path in IDENTITIES_DIR.glob("*.txt"):
        names.update(re.findall(r"^(identity_\w+)\s*=\s*\{", strip_comments(path.read_text(encoding="utf-8-sig")), re.M))
    return names


def defaults(path):
    """{piece: set of identities} from a file of INJECT:<piece> = { default_choice_for_identities = { ... } }."""
    text = strip_comments(path.read_text(encoding="utf-8-sig"))
    pieces = {}
    for m in re.finditer(r"^INJECT:(\w+)\s*=\s*\{\s*default_choice_for_identities\s*=\s*\{([^}]*)\}\s*\}", text, re.M):
        pieces.setdefault(m.group(1), set()).update(m.group(2).split())
    return pieces


def by_identity(pieces):
    out = {}
    for piece, ids in pieces.items():
        for identity in ids:
            out.setdefault(identity, set()).add(piece)
    return out


# A worktree made with the older sparse recipe has no gfx/map/ (docs/guides/git_workflow.md); CI's checkout has it,
# so there a missing file still fails.
@unittest.skipUnless(STATUES.is_dir() or "CI" in os.environ, "gfx/map/ not checked out (sparse worktree)")
class TestStatueDefaults(unittest.TestCase):
    def test_every_mod_identity_has_a_hero_and_a_pedestal(self):
        heroes, pedestals = by_identity(defaults(HEROES)), by_identity(defaults(PEDESTALS))
        for identity in sorted(mod_identities()):
            with self.subTest(identity=identity):
                self.assertIn(identity, NEAREST, "a new mod identity: pick its nearest vanilla identity and add it here and to the two statue files")
                self.assertTrue(heroes.get(identity), "no statue hero lists it")
                self.assertTrue(pedestals.get(identity), "no statue pedestal lists it")

    def test_each_takes_the_pieces_of_its_nearest_vanilla_identity(self):
        heroes, pedestals = by_identity(defaults(HEROES)), by_identity(defaults(PEDESTALS))
        for identity, vanilla in NEAREST.items():
            with self.subTest(identity=identity):
                self.assertEqual(heroes.get(identity), VANILLA_HEROES[vanilla])
                self.assertEqual(pedestals.get(identity), VANILLA_PEDESTALS[vanilla])

    def test_the_files_list_only_mod_identities(self):
        # An injected list is taken to add to vanilla's; restating a vanilla identity would list it twice.
        mod = mod_identities()
        for path in (HEROES, PEDESTALS):
            for piece, ids in defaults(path).items():
                with self.subTest(file=path.name, piece=piece):
                    self.assertLessEqual(ids, mod)

    def test_every_inject_is_read(self):
        for path in (HEROES, PEDESTALS):
            text = strip_comments(path.read_text(encoding="utf-8-sig"))
            with self.subTest(file=path.name):
                self.assertEqual(len(re.findall(r"^INJECT:", text, re.M)), len(defaults(path)))
                self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
