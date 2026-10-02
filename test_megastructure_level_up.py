"""Guards the level-up a finished megastructure construction site performs.

`create_building` on a building the state already has gives no predictable
level, and owned and unowned wonders disagree (seen in game, 2026-10-02):

    Space Elevator (self)                    level 1, asked 2 -> 3
    Space Elevator (self)                    level 3, asked 1 -> 3
    Nanofabrication Center (self)            level 3, asked 4 -> 7
    Orbital Solar Collector (no_ownership)   level 1, asked 2 -> 2

An owned wonder is therefore rebuilt at its level + 1 (remove, then build at
that level) instead of being asked for a level, and an unowned one keeps the
current-level-plus-one chain. Each wonder's wrapper in extra_effects.txt says
which form it needs, and that flag must agree with the building's
`ownership_type`.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EFFECTS = ROOT / "common" / "scripted_effects" / "extra_effects.txt"
BUILDINGS = ROOT / "common" / "buildings" / "extra_buildings.txt"

WONDERS = [
    "space_elevator",
    "solar_collector",
    "orbital_battlestation",
    "mind_upload_nexus",
    "antimatter_facility",
    "nanofabrication_center",
    "consciousness_network",
]


def _read(path):
    return path.read_text(encoding="utf-8-sig")


def _block(text, header):
    """Body of the brace block opened by the first match of `header`.

    `header` must end at the block's opening brace, or inside the block.
    """
    match = re.search(header, text, re.M)
    if match is None:
        return None
    depth, i = 1, match.end()
    while depth:
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[match.end():i - 1]


def _base():
    body = _block(_read(EFFECTS), r"^generic_wonder_construction_base\s*=\s*\{")
    assert body is not None, "generic_wonder_construction_base not found"
    return body


def _rebuild_branch():
    # The `if = { limit = { always = $REBUILD$ } ... }` block: matching up to
    # the end of its limit leaves the scan inside that `if`.
    branch = _block(_base(), r"limit\s*=\s*\{\s*always\s*=\s*\$REBUILD\$\s*\}")
    assert branch is not None, "rebuild branch not found"
    return branch


def _ownership_type(wonder):
    body = _block(
        _read(BUILDINGS),
        rf"^REPLACE_OR_CREATE:building_{wonder}\s*=\s*\{{",
    )
    assert body is not None, f"building_{wonder} not found"
    match = re.search(r"ownership_type\s*=\s*(\w+)", body)
    return match.group(1) if match else "default"


def _rebuild_flag(wonder):
    match = re.search(
        rf"^{wonder}_construction\s*=\s*\{{\s*generic_wonder_construction_base"
        rf"\s*=\s*\{{([^}}]*)\}}\s*\}}",
        _read(EFFECTS),
        re.M,
    )
    assert match is not None, f"{wonder}_construction wrapper not found"
    flag = re.search(r"REBUILD\s*=\s*(\w+)", match.group(1))
    return flag.group(1) if flag else None


class MegastructureLevelUpTests(unittest.TestCase):
    def test_every_wrapper_declares_its_level_up_form(self):
        for wonder in WONDERS:
            with self.subTest(wonder=wonder):
                self.assertIn(_rebuild_flag(wonder), ("yes", "no"))

    def test_flag_agrees_with_ownership_type(self):
        for wonder in WONDERS:
            with self.subTest(wonder=wonder):
                owned = _ownership_type(wonder) != "no_ownership"
                self.assertEqual(
                    _rebuild_flag(wonder),
                    "yes" if owned else "no",
                    f"building_{wonder} has ownership_type "
                    f"{_ownership_type(wonder)}: an owned wonder must be "
                    "rebuilt, an unowned one asked for level + 1",
                )

    def test_owned_wonder_is_rebuilt_never_asked_for_a_level(self):
        branch = _rebuild_branch()
        self.assertNotIn(
            "create_building",
            branch,
            "create_building on an existing owned wonder over-levels it "
            "(level 3 asked for 4 gave 7) or does nothing (asked for 1 at "
            "level 3); rebuild through remove_building instead",
        )
        removed = branch.index("remove_building = building_$WONDER$")
        rebuilt = branch.index("te_construction_market_build_specified_level")
        self.assertLess(removed, rebuilt)
        self.assertIn("SPEC_LEVEL = var:wonder_rebuild_level", branch)

    def test_rebuild_level_is_saved_before_removal_and_is_one_higher(self):
        branch = _rebuild_branch()
        saved = branch.index("value = b:building_$WONDER$.level")
        bumped = re.search(
            r"change_variable\s*=\s*\{\s*name\s*=\s*wonder_rebuild_level\s+add\s*=\s*1\s*\}",
            branch,
        )
        self.assertIsNotNone(bumped)
        removed = branch.index("remove_building = building_$WONDER$")
        self.assertLess(saved, bumped.start())
        self.assertLess(bumped.start(), removed)

    def test_rebuild_is_capped_and_clears_its_variable(self):
        branch = _rebuild_branch()
        self.assertRegex(
            branch, r"limit\s*=\s*\{\s*b:building_\$WONDER\$\.level\s*<\s*\$MAX_LEVEL\$\s*\}"
        )
        self.assertIn("remove_variable = wonder_rebuild_level", branch)

    def test_unowned_chain_asks_for_current_level_plus_one(self):
        pairs = re.findall(
            r"level\s*=\s*(\d+)\s+b:building_\$WONDER\$\.level\s*<\s*\$MAX_LEVEL\$\s*\}"
            r"\s*create_building\s*=\s*\{[^}]*level\s*=\s*(\d+)",
            _base(),
        )
        self.assertEqual(len(pairs), 19)
        for current, asked in pairs:
            self.assertEqual(int(asked), int(current) + 1)


if __name__ == "__main__":
    unittest.main()
