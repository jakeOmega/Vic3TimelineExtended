"""GET /building-groups and the parent_group hierarchy behind it (#383):
building_group_tree.Tree over a real ModState, and the server's handler
called in-process. No game install and no running server needed."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import building_group_tree as bgt
import mod_state_server as mss
import vanilla_parsed
from mod_state import ModState

REPO = Path(__file__).resolve().parent

VANILLA_GROUPS = """
bg_manufacturing = {
	category = urban
}
bg_heavy_industry = {
	parent_group = bg_manufacturing
	construction_efficiency_modifier = yes
}
bg_construction = {
	parent_group = bg_manufacturing
}
bg_power = {
	category = urban
}
bg_agriculture = {
	construction_efficiency_modifier = yes
}
bg_plantations = {
	category = rural
}
"""

# The mod's own shapes: a new group under a vanilla one, a child of that new
# group, a REPLACE that moves a vanilla group, and an INJECT.
MOD_GROUPS = """
REPLACE_OR_CREATE:bg_high_tech = {
	parent_group = bg_heavy_industry

	construction_efficiency_modifier = yes
}
REPLACE_OR_CREATE:bg_exotic = {
	parent_group = bg_high_tech
}
REPLACE:bg_construction = {
	parent_group = bg_heavy_industry
}
INJECT:bg_power = {
	construction_efficiency_modifier = yes
}
"""

VANILLA_BUILDINGS = """
building_steel_mill = { building_group = bg_heavy_industry }
building_construction_sector = { building_group = bg_construction }
building_power_plant = { building_group = bg_power }
building_vineyard = { building_group = bg_agriculture }
building_coffee_plantation = { building_group = bg_plantations }
"""

MOD_BUILDINGS = """
building_software_industry = { building_group = bg_high_tech }
building_space_mine = { building_group = bg_exotic }
"""


def _state():
    """A ModState over a small vanilla and mod, with the mod root on disk."""
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    files = {
        ("game", "building_groups"): VANILLA_GROUPS, ("mod", "building_groups"): MOD_GROUPS,
        ("game", "buildings"): VANILLA_BUILDINGS, ("mod", "buildings"): MOD_BUILDINGS,
    }
    for (side, folder), text in files.items():
        (root / side / "common" / folder).mkdir(parents=True)
        (root / side / "common" / folder / "00_file.txt").write_text(text, encoding="utf-8")

    def dirs(side):
        return {"Building Groups": str(root / side / "common" / "building_groups"),
                "Buildings": str(root / side / "common" / "buildings")}

    state = ModState(dirs("game"), dirs("mod"))
    state.localization = {"bg_high_tech": "High-Tech Industry",
                          "building_space_mine": "Extraplanetary Base"}
    return tmp, root / "mod", state


def _tree(state):
    return bgt.Tree(state.get_data("Building Groups"),
                    state.base_parsers["Building Groups"].data,
                    state.get_data("Buildings"))


class TreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.mod_root, cls.state = _state()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.tree = _tree(cls.state)

    def test_parent_is_the_merged_value(self):
        # REPLACE moved bg_construction from bg_manufacturing.
        self.assertEqual(self.tree.parent["bg_construction"], "bg_heavy_industry")
        self.assertEqual(self.tree.parent["bg_high_tech"], "bg_heavy_industry")
        self.assertIsNone(self.tree.parent["bg_manufacturing"])

    def test_origin(self):
        self.assertEqual(self.tree.origin("bg_heavy_industry"), "vanilla")
        self.assertEqual(self.tree.origin("bg_high_tech"), "mod")
        self.assertEqual(self.tree.origin("bg_construction"), "mod-replaced")
        self.assertEqual(self.tree.origin("bg_power"), "mod-replaced")   # INJECT

    def test_construction_efficiency_modifier_is_the_groups_own_flag(self):
        self.assertTrue(self.tree.row("bg_heavy_industry")["construction_efficiency_modifier"])
        self.assertTrue(self.tree.row("bg_power")["construction_efficiency_modifier"])
        # Its parent sets the flag; bg_exotic itself does not.
        self.assertFalse(self.tree.row("bg_exotic")["construction_efficiency_modifier"])

    def test_ancestors_nearest_first(self):
        self.assertEqual(self.tree.ancestors("bg_exotic"),
                         ["bg_high_tech", "bg_heavy_industry", "bg_manufacturing"])
        self.assertEqual(self.tree.ancestors("bg_agriculture"), [])

    def test_descendants_parent_before_child(self):
        self.assertEqual(self.tree.descendants("bg_heavy_industry"),
                         ["bg_construction", "bg_high_tech", "bg_exotic"])
        self.assertEqual(self.tree.descendants("bg_agriculture"), [])

    def test_reach_walks_descendants(self):
        self.assertEqual(self.tree.reach("bg_heavy_industry"), [
            ("building_steel_mill", "bg_heavy_industry"),
            ("building_construction_sector", "bg_construction"),
            ("building_software_industry", "bg_high_tech"),
            ("building_space_mine", "bg_exotic"),
        ])
        # Top-level siblings: agriculture's modifiers do not reach plantations.
        self.assertEqual(self.tree.reach("bg_agriculture"),
                         [("building_vineyard", "bg_agriculture")])

    def test_resolve_takes_the_prefixless_spelling(self):
        self.assertEqual(self.tree.resolve("bg_power"), "bg_power")
        self.assertEqual(self.tree.resolve("power"), "bg_power")
        self.assertIsNone(self.tree.resolve("nope"))

    def test_a_cycle_or_an_unknown_parent_ends_the_walk(self):
        groups = {
            "bg_a": ("=", {"parent_group": ("=", "bg_b")}),
            "bg_b": ("=", {"parent_group": ("=", "bg_a")}),
            "bg_c": ("=", {"parent_group": ("=", "bg_gone")}),
        }
        tree = bgt.Tree(groups)
        self.assertEqual(tree.ancestors("bg_a"), ["bg_b"])
        self.assertEqual(tree.descendants("bg_a"), ["bg_b"])
        self.assertEqual(tree.ancestors("bg_c"), ["bg_gone"])

    def test_mod_definitions_name_file_line_and_directive(self):
        self.assertEqual(bgt.mod_definitions(str(self.mod_root), "bg_power"), [
            {"file": "common/building_groups/00_file.txt", "line": 13, "directive": "INJECT"}])
        self.assertEqual(bgt.mod_definitions(str(self.mod_root), "bg_heavy_industry"), [])
        self.assertEqual(bgt.mod_definitions("/nonexistent", "bg_power"), [])


class HandlerTests(unittest.TestCase):
    """ModStateHandler.route on /building-groups, no socket and no server."""

    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.mod_root, cls.state = _state()
        cls.addClassCleanup(cls.tmp.cleanup)

    def get(self, *parts):
        handler = object.__new__(mss.ModStateHandler)
        with mock.patch.object(mss, "ms", self.state), \
                mock.patch.object(mss, "mod_path", str(self.mod_root)):
            return handler.route(["building-groups", *parts], {})

    def test_listing_keeps_the_vocab_shape(self):
        out = self.get()
        self.assertEqual(out["placeholder"], "bg")
        self.assertEqual(out["entity_type"], "Building Groups")
        self.assertEqual(out["count"], len(out["entries"]))
        self.assertEqual(out["group_count"], 8)
        for entry in out["entries"]:
            self.assertIn("id", entry)
            self.assertIn("name", entry)
        json.dumps(out)

    def test_listing_entries_carry_the_hierarchy(self):
        entries = {e["id"]: e for e in self.get()["entries"]}
        self.assertEqual(entries["bg_high_tech"], {
            "id": "bg_high_tech", "name": "High-Tech Industry",
            "parent_group": "bg_heavy_industry", "origin": "mod",
            "construction_efficiency_modifier": True,
        })
        self.assertEqual(entries["bg_construction"]["origin"], "mod-replaced")
        self.assertEqual(entries["bg_construction"]["parent_group"], "bg_heavy_industry")
        self.assertIsNone(entries["bg_agriculture"]["parent_group"])
        self.assertEqual(entries["bg_agriculture"]["origin"], "vanilla")

    def test_prefixless_entries_are_marked_as_aliases(self):
        entries = {e["id"]: e for e in self.get()["entries"]}
        self.assertEqual(entries["high_tech"],
                         {"id": "high_tech", "name": "high_tech", "alias_of": "bg_high_tech"})

    def test_detail(self):
        out = self.get("bg_high_tech")
        self.assertEqual(out, {
            "type": "Building Groups", "id": "bg_high_tech", "name": "High-Tech Industry",
            "parent_group": "bg_heavy_industry", "origin": "mod",
            "construction_efficiency_modifier": True,
            "ancestors": ["bg_heavy_industry", "bg_manufacturing"],
            "children": ["bg_exotic"],
            "descendants": ["bg_exotic"],
            "buildings": [{"id": "building_software_industry",
                           "name": "building_software_industry"}],
            "mod_definitions": [{"file": "common/building_groups/00_file.txt", "line": 2,
                                 "directive": "REPLACE_OR_CREATE"}],
        })

    def test_reach(self):
        out = self.get("bg_high_tech", "reach")
        self.assertEqual(out["groups"], ["bg_high_tech", "bg_exotic"])
        self.assertEqual(out["count"], 2)
        self.assertEqual(out["buildings"], [
            {"id": "building_software_industry", "name": "building_software_industry",
             "building_group": "bg_high_tech"},
            {"id": "building_space_mine", "name": "Extraplanetary Base",
             "building_group": "bg_exotic"},
        ])
        self.assertIn("note", out)

    def test_detail_takes_the_alias(self):
        self.assertEqual(self.get("high_tech")["id"], "bg_high_tech")

    def test_unknown_group_or_sub_route_is_404(self):
        for parts in (("bg_nope",), ("bg_power", "nope"), ("bg_power", "reach", "x")):
            with self.subTest(parts=parts), self.assertRaises(mss.NotFound):
                self.get(*parts)

    def test_no_group_data_keeps_the_plain_listing(self):
        handler = object.__new__(mss.ModStateHandler)
        stub = mock.Mock()
        stub.get_data.return_value = None
        with mock.patch.object(mss, "ms", stub), \
                mock.patch.object(mss, "_vocabulary_values", return_value=["bg_x"]):
            stub.localize.side_effect = lambda key: key
            out = handler.route(["building-groups"], {})
            self.assertEqual(out["entries"], [{"id": "bg_x", "name": "bg_x"}])
            with self.assertRaises(mss.DataNotLoaded):
                handler.route(["building-groups", "bg_x"], {})


class CommittedDataTests(unittest.TestCase):
    """The mod's own groups over the committed vanilla snapshot: the two
    questions #383 could not answer from the server."""

    @classmethod
    def setUpClass(cls):
        vanilla = {}
        for entity_type, name in (("Building Groups", "building_groups"), ("Buildings", "buildings")):
            with open(REPO / "vanilla_parsed" / "common" / f"{name}.json", encoding="utf-8") as f:
                vanilla[entity_type] = vanilla_parsed.decode(json.load(f))
        mod_dirs = {"Building Groups": str(REPO / "common" / "building_groups"),
                    "Buildings": str(REPO / "common" / "buildings")}
        cls.state = ModState(dict.fromkeys(mod_dirs, "/nonexistent"), mod_dirs,
                             vanilla_data=vanilla)
        cls.tree = _tree(cls.state)

    def test_high_tech_sits_under_heavy_industry(self):
        self.assertEqual(self.tree.parent["bg_high_tech"], "bg_heavy_industry")
        self.assertIn("bg_high_tech", self.tree.descendants("bg_heavy_industry"))
        reached = {group for _b, group in self.tree.reach("bg_heavy_industry")}
        self.assertIn("bg_high_tech", reached)

    def test_agriculture_does_not_cover_plantations_or_ranching(self):
        below = self.tree.descendants("bg_agriculture")
        for group in ("bg_plantations", "bg_ranching"):
            self.assertIn(group, self.tree.groups)
            self.assertNotIn(group, below)
            self.assertNotIn("bg_agriculture", self.tree.ancestors(group))

    def test_every_vanilla_group_has_an_origin_and_untouched_ones_read_vanilla(self):
        origins = {gid: self.tree.origin(gid) for gid in self.tree.groups}
        self.assertEqual(origins["bg_manufacturing"], "vanilla")
        self.assertEqual(origins["bg_high_tech"], "mod")
        self.assertEqual(origins["bg_power"], "mod-replaced")
        self.assertEqual(set(origins.values()), {"vanilla", "mod", "mod-replaced"})

    def test_every_parent_is_a_known_group(self):
        for gid, parent in self.tree.parent.items():
            if parent is not None:
                self.assertIn(parent, self.tree.groups, gid)


if __name__ == "__main__":
    unittest.main()
