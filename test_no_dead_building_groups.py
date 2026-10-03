"""No mod file may use one of vanilla's legacy building groups.

Vanilla keeps 21 building groups (`bg_coal_mining`, `bg_wheat_farms`, ...) "only
for save game compatibility"; its own comment says they are not actually used
(`common/building_groups/00_building_groups.txt`, TODO PRCAL-42162). No building
belongs to one: the coal mine sits in `bg_mining` with the iron, gold, lead and
sulfur mines, and farms and plantations sit in `bg_agriculture` and
`bg_plantations`. A `building_group_<legacy group>_*` modifier therefore matches
no building. The engine accepts the key without a word, so the modifier does
nothing and neither the log nor the tooltip says so.

The mod shipped seven such modifier lines (carbon tax, divestment, fossil lobby
concessions twice, climate accord rejection twice, the Enforce Emissions Reduction treaty)
before this test; they now use `building_coal_mine_*`, which is live. This
fails if a legacy group, or a modifier key built from one, appears in any file
the game or the player guide reads.
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# The legacy groups of vanilla 1.14.5: each is declared with a `default_building`
# and nothing else, and no building names one in `building_group`.
LEGACY_GROUPS = (
    "bg_iron_mining", "bg_sulfur_mining", "bg_coal_mining", "bg_gold_mining",
    "bg_lead_mining", "bg_rye_farms", "bg_rice_farms", "bg_maize_farms",
    "bg_wheat_farms", "bg_millet_farms", "bg_vineyard_plantations",
    "bg_cotton_plantations", "bg_livestock_ranches", "bg_tobacco_plantations",
    "bg_banana_plantations", "bg_coffee_plantations", "bg_silk_plantations",
    "bg_dye_plantations", "bg_opium_plantations", "bg_tea_plantations",
    "bg_sugar_plantations",
)

# Folders whose files the game or the player reads, and the suffixes to scan.
# `docs/engine/` is generated from the modifier registry (it lists the vanilla
# keys whatever the mod does) and the other docs only name the groups to explain
# this very bug, so neither is scanned.
SCANNED = {
    "common": (".txt",),
    "events": (".txt",),
    "gui": (".gui", ".txt"),
    "localization": (".yml",),
    "map_data": (".txt",),
    "docs/player_guide": (".md",),
}

# Files that may name a legacy group, with the reason. Empty on purpose.
ALLOWED = {}

PATTERN = re.compile(
    r"(?<![a-z0-9])(" + "|".join(LEGACY_GROUPS) + r")(?![a-z0-9])"
)


def _scanned_files():
    for folder, suffixes in SCANNED.items():
        base = ROOT / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in suffixes:
                yield path


class NoDeadBuildingGroupsTest(unittest.TestCase):
    def test_no_file_names_a_legacy_building_group(self):
        found = []
        for path in _scanned_files():
            rel = path.relative_to(ROOT).as_posix()
            if rel in ALLOWED:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            for number, line in enumerate(text.splitlines(), 1):
                match = PATTERN.search(line)
                if match:
                    found.append(f"{rel}:{number}: {match.group(1)}: {line.strip()[:100]}")
        self.assertEqual(
            found, [],
            "These lines name a vanilla legacy building group, which no building "
            "belongs to, so a modifier keyed on it does nothing. Use the building's "
            "own key (building_coal_mine_throughput_add) or the live group "
            "(building_group_bg_mining_*):\n" + "\n".join(found),
        )

    def test_the_legacy_groups_are_really_unused(self):
        """Guards the list above: a group a building belongs to is not legacy."""
        used = set()
        buildings = ROOT / "vanilla_parsed/common/buildings.json"
        if buildings.is_file():
            for entry in json.loads(buildings.read_text(encoding="utf-8")).values():
                body = entry[1] if isinstance(entry, list) and len(entry) > 1 else None
                if isinstance(body, dict) and "building_group" in body:
                    used.add(body["building_group"][1])
        for path in (ROOT / "common/buildings").rglob("*.txt"):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            used.update(re.findall(r"\bbuilding_group\s*=\s*(\w+)", text))
        self.assertEqual(sorted(set(LEGACY_GROUPS) & used), [])

    def test_the_coal_mine_sits_in_the_mining_group(self):
        """Why `building_group_bg_coal_mining_*` was dead, and what is live instead."""
        buildings = ROOT / "vanilla_parsed/common/buildings.json"
        if not buildings.is_file():
            self.skipTest("vanilla_parsed is absent")
        coal = json.loads(buildings.read_text(encoding="utf-8"))["building_coal_mine"][1]
        self.assertEqual(coal["building_group"][1], "bg_mining")


if __name__ == "__main__":
    unittest.main()
