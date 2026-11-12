"""The building-group hierarchy for GET /building-groups (#383).

A building group names its parent with `parent_group`, and a
`building_group_<group>_*` modifier reaches the buildings of that group and of
every group below it. The mod's `REPLACE_OR_CREATE:bg_high_tech` sets
`parent_group = bg_heavy_industry`, so
`building_group_bg_heavy_industry_construction_efficiency_add` also speeds up
every high-tech building. `Tree` answers that from ModState's merged
"Building Groups" and "Buildings": a group's parent, ancestors, descendants,
the buildings directly in it, and the buildings its modifiers reach.

`origin` compares the merged group with vanilla's: `vanilla` (untouched),
`mod` (vanilla has no such group) or `mod-replaced` (a vanilla group a mod
file redefines or injects into; `mod_definitions` gives each mod file's line
and directive).
"""
from __future__ import annotations

import os
from typing import Optional

import external_mod_overlap as ext
from party_catalog import field

ENTITY_TYPE = "Building Groups"
DB = "building_groups"
VANILLA, MOD, MOD_REPLACED = "vanilla", "mod", "mod-replaced"
REACH_NOTE = (
    "A building_group_<id>_* modifier applies to the buildings of the group and of every "
    "group below it (parent_group, after the mod's REPLACE / INJECT are applied)."
)


def _scalar(entity, name: str) -> Optional[str]:
    """`name`'s value in a parsed entity when it is a plain token, else None."""
    value = field(entity, name)
    if isinstance(value, tuple) and len(value) >= 2:
        value = value[1]
    return value if isinstance(value, str) else None


class Tree:
    def __init__(self, groups: dict, vanilla_groups: Optional[dict] = None,
                 buildings: Optional[dict] = None):
        self.groups = groups or {}
        self.vanilla = vanilla_groups or {}
        self.parent = {gid: _scalar(raw, "parent_group") for gid, raw in self.groups.items()}
        self.children: dict = {gid: [] for gid in self.groups}
        for gid, parent in self.parent.items():
            if parent in self.children:
                self.children[parent].append(gid)
        self.buildings: dict = {gid: [] for gid in self.groups}
        self.building_group: dict = {}
        for bid, raw in (buildings or {}).items():
            group = _scalar(raw, "building_group")
            self.building_group[bid] = group
            if group in self.buildings:
                self.buildings[group].append(bid)

    def resolve(self, name: str) -> Optional[str]:
        """The group `name` means: itself, or `bg_<name>` for the prefix-less
        spelling the modifier vocabulary lists beside each group."""
        if name in self.groups:
            return name
        return f"bg_{name}" if f"bg_{name}" in self.groups else None

    def origin(self, gid: str) -> str:
        if gid not in self.vanilla:
            return MOD
        return VANILLA if self.vanilla[gid] == self.groups[gid] else MOD_REPLACED

    def row(self, gid: str) -> dict:
        """The fields every /building-groups entry of a real group carries."""
        return {
            "parent_group": self.parent[gid],
            "origin": self.origin(gid),
            # Whether the group registers its own
            # building_group_<id>_construction_efficiency_add.
            "construction_efficiency_modifier":
                _scalar(self.groups[gid], "construction_efficiency_modifier") == "yes",
        }

    def ancestors(self, gid: str) -> list:
        """The parent chain, nearest first. Stops at a group that names no
        parent, an unknown one (listed, as the last entry) or a cycle."""
        out, seen = [], {gid}
        parent = self.parent.get(gid)
        while parent and parent not in seen:
            out.append(parent)
            seen.add(parent)
            parent = self.parent.get(parent)
        return out

    def descendants(self, gid: str) -> list:
        """Every group below `gid`, each parent before its children."""
        out, seen, todo = [], {gid}, list(self.children.get(gid, []))
        while todo:
            current = todo.pop(0)
            if current in seen:
                continue
            seen.add(current)
            out.append(current)
            todo.extend(self.children.get(current, []))
        return out

    def reach(self, gid: str) -> list:
        """(building, its group) for every building in `gid` or below it."""
        return [(bid, group) for group in [gid, *self.descendants(gid)]
                for bid in self.buildings.get(group, [])]


def mod_definitions(mod_root: str, gid: str) -> list:
    """Each mod file's definition of group `gid`: `{file, line, directive}`
    (`directive` None for a bare definition), read from
    `<mod_root>/common/building_groups` now."""
    base = os.path.join(mod_root, "common", DB)
    if not os.path.isdir(base):
        return []
    scan = ext._scan_db(mod_root, DB, ext.list_files(base), [], ext.OURS)
    return [{"file": f"common/{DB}/{rel}", "line": entry.line, "directive": entry.directive}
            for rel, entry in scan.entries.get(gid, [])]
