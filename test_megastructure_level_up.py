"""Guards the level-up a finished megastructure construction site performs.

`create_building` on a building the state already has behaves by the building's
`ownership_type`: an owned building (`self`) stacks the level it is given onto
its own, an unowned one (`no_ownership`) keeps the larger of the two. Asking a
level-3 Nanofabrication Center (`self`) for "level 4" gave level 7. Each
wonder's wrapper in extra_effects.txt must therefore say which form it needs,
and that flag must agree with the building's `ownership_type`.
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
    """Body of the brace block opened by the first match of `header`."""
    match = re.search(header, text, re.M)
    if match is None:
        return None
    depth, i = 1, match.end()
    while depth:
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[match.end():i - 1]


def _ownership_type(wonder):
    body = _block(
        _read(BUILDINGS),
        rf"^REPLACE_OR_CREATE:building_{wonder}\s*=\s*\{{",
    )
    assert body is not None, f"building_{wonder} not found"
    match = re.search(r"ownership_type\s*=\s*(\w+)", body)
    return match.group(1) if match else "default"


def _stacks_levels_flag(wonder):
    match = re.search(
        rf"^{wonder}_construction\s*=\s*\{{\s*generic_wonder_construction_base"
        rf"\s*=\s*\{{([^}}]*)\}}\s*\}}",
        _read(EFFECTS),
        re.M,
    )
    assert match is not None, f"{wonder}_construction wrapper not found"
    flag = re.search(r"STACKS_LEVELS\s*=\s*(\w+)", match.group(1))
    return flag.group(1) if flag else None


class MegastructureLevelUpTests(unittest.TestCase):
    def test_every_wrapper_declares_its_level_up_form(self):
        for wonder in WONDERS:
            with self.subTest(wonder=wonder):
                self.assertIn(_stacks_levels_flag(wonder), ("yes", "no"))

    def test_flag_agrees_with_ownership_type(self):
        for wonder in WONDERS:
            with self.subTest(wonder=wonder):
                owned = _ownership_type(wonder) != "no_ownership"
                self.assertEqual(
                    _stacks_levels_flag(wonder),
                    "yes" if owned else "no",
                    f"building_{wonder} has ownership_type "
                    f"{_ownership_type(wonder)}: an owned building stacks the "
                    "level it is given, an unowned one keeps the larger level",
                )

    def test_stacking_form_asks_for_exactly_one_level(self):
        base = _block(
            _read(EFFECTS), r"^generic_wonder_construction_base\s*=\s*\{"
        )
        stacking = _block(base, r"limit\s*=\s*\{\s*always\s*=\s*\$STACKS_LEVELS\$\s*\}\s*")
        # `_block` starts after the matched header; the stacking branch is the
        # `if = { limit = { always = $STACKS_LEVELS$ } ... }` block, whose body
        # runs on to the closing brace of that `if`.
        self.assertIsNotNone(stacking)
        levels = re.findall(r"create_building\s*=\s*\{[^}]*level\s*=\s*(\d+)", stacking)
        self.assertEqual(levels[:1], ["1"])

    def test_set_form_asks_for_current_level_plus_one(self):
        base = _block(
            _read(EFFECTS), r"^generic_wonder_construction_base\s*=\s*\{"
        )
        pairs = re.findall(
            r"level\s*=\s*(\d+)\s+b:building_\$WONDER\$\.level\s*<\s*\$MAX_LEVEL\$\s*\}"
            r"\s*create_building\s*=\s*\{[^}]*level\s*=\s*(\d+)",
            base,
        )
        self.assertEqual(len(pairs), 19)
        for current, asked in pairs:
            self.assertEqual(int(asked), int(current) + 1)


if __name__ == "__main__":
    unittest.main()
