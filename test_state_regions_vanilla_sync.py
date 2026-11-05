"""map_data/state_regions/ against vanilla's map, and resources.py's deposit rule (docs/auto_generated_files.md).

The mod ships a full copy of every vanilla state-region file, written by resources.py. When a patch changes
vanilla's map and the copies are not rewritten, the engine reads the old map under the new history: 1.15
renamed three states, added two, merged Chukotka into Kamchatka, redrew provinces in Russia and added a
cold-effect pair to most regions, and the first 1.15 launch with the 1.14.5 copies logged history naming
missing states, `Province crossing multiple state regions` and invalid strategic regions.

Game-free checks (CI): the committed copies are one consistent map (no repeated state key, no province in two
states), every key the two configs name is a state in it, and the deposit rule's text edits. With the game
installed: the copies hold exactly vanilla's states, ids, provinces, naval exits and cold fields, there is no
file vanilla lacks, and a fresh run of resources.py reproduces them byte for byte.

    python3 test_state_regions_vanilla_sync.py
"""
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGIONS = ROOT / "map_data" / "state_regions"

_spec = importlib.util.spec_from_file_location("resources", ROOT / "resources.py")
resources = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(resources)

GAME = Path(resources.base_game_path) / "game"
VANILLA_REGIONS = GAME / "map_data" / "state_regions"
HAVE_GAME = VANILLA_REGIONS.is_dir() and any(VANILLA_REGIONS.glob("*.txt"))


def read_states(root):
    """{state: {"file", "id", "provinces", "naval_exit_id", "min_cold_effect", "max_cold_effect"}}; repeats raise."""
    out = {}
    for path in sorted(Path(root).glob("*.txt")):
        text = "\n".join(line.split("#")[0] for line in path.read_text(encoding="utf-8-sig").split("\n"))
        for name, start, end in resources.iter_state_blocks(text):
            if name in out:
                raise AssertionError(f"{name} defined in both {out[name]['file']} and {path.name}")
            body = text[start:end]
            provinces = re.search(r"provinces\s*=\s*\{([^}]*)\}", body)
            state = {"file": path.name,
                     "provinces": set(re.findall(r"x[0-9A-Fa-f]{6}", provinces.group(1))) if provinces else set()}
            for field in ("id", "naval_exit_id", "min_cold_effect", "max_cold_effect"):
                m = re.search(rf"(?m)^\s*{field}\s*=\s*(\S+)", body)
                state[field] = m.group(1) if m else None
            out[name] = state
    return out


BLOCK = ('STATE_X = {\n    id = 1\n    subsistence_building = "building_subsistence_farm"\n'
         '    capped_resources = {\n        building_iron_mine = 60\n        building_copper_mine = 30\n    }\n'
         '    naval_exit_id = 3000\n    min_cold_effect = 0.04\n    max_cold_effect = 0.71\n}\n')
COPPER = {"STATE_X": {"Copper": 10}}  # 800 levels


class DepositRule(unittest.TestCase):
    """A deposit for a building vanilla already caps in the state: one entry, the larger figure."""

    def caps(self, text):
        m = resources.CAPPED_RE.search(text)
        return dict(resources.CAPPED_ENTRY_RE.findall(m.group(2))) if m else {}

    def test_capped_building_raises_vanilla_cap(self):
        out = resources.process_state_block(BLOCK, "STATE_X", COPPER, discoverable={"building_copper_mine": False})
        self.assertEqual(self.caps(out), {"building_iron_mine": "60", "building_copper_mine": "800"})
        self.assertNotIn("resource = {", out)
        self.assertIn("max_cold_effect = 0.71", out)

    def test_capped_building_keeps_a_larger_vanilla_cap(self):
        block = BLOCK.replace("building_copper_mine = 30", "building_copper_mine = 900")
        self.assertEqual(
            resources.process_state_block(block, "STATE_X", COPPER, discoverable={"building_copper_mine": False}),
            block)

    def test_capped_building_without_a_vanilla_entry_gets_one(self):
        block = BLOCK.replace("        building_copper_mine = 30\n", "")
        out = resources.process_state_block(block, "STATE_X", COPPER, discoverable={"building_copper_mine": False})
        self.assertEqual(self.caps(out)["building_copper_mine"], "800")
        bare = re.sub(r"    capped_resources = \{[^}]*\}\n", "", BLOCK)
        out = resources.process_state_block(bare, "STATE_X", COPPER, discoverable={"building_copper_mine": False})
        self.assertEqual(self.caps(out), {"building_copper_mine": "800"})
        self.assertLess(out.index("capped_resources"), out.index("naval_exit_id"))

    def test_discoverable_building_keeps_vanilla_cap_as_discovered(self):
        out = resources.process_state_block(BLOCK, "STATE_X", COPPER, discoverable={"building_copper_mine": True})
        self.assertEqual(self.caps(out), {"building_iron_mine": "60"})
        block = re.search(r'resource = \{\s*type = "building_copper_mine"([^}]*)\}', out)
        self.assertIsNotNone(block)
        self.assertIn("undiscovered_amount = 770", block.group(1))
        self.assertIn("discovered_amount = 30", block.group(1))
        self.assertEqual(out.count("building_copper_mine"), 1)

    def test_discoverable_building_converts_unconfigured_vanilla_caps(self):
        out = resources.process_state_block(BLOCK, "STATE_X", {}, discoverable={"building_copper_mine": True})
        block = re.search(r'resource = \{\s*type = "building_copper_mine"([^}]*)\}', out)
        self.assertEqual(re.findall(r"(\w+_amount) = (\d+)", block.group(1)), [("discovered_amount", "30")])
        only_copper = BLOCK.replace("        building_iron_mine = 60\n", "")
        out = resources.process_state_block(only_copper, "STATE_X", {}, discoverable={"building_copper_mine": True})
        self.assertNotIn("capped_resources", out)

    def test_discoverable_building_without_a_vanilla_cap_is_undiscovered(self):
        out = resources.process_state_block(BLOCK, "STATE_X", {"STATE_X": {"Lithium": 10}},
                                            discoverable={"building_lithium_mine": True})
        self.assertIn('type = "building_lithium_mine"\n        undiscovered_amount = 200\n', out)
        self.assertEqual(self.caps(out)["building_copper_mine"], "30")


class BuildingGroups(unittest.TestCase):
    """discoverable_buildings() reads the group the engine would keep."""

    def resolve(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            for rel, text in files.items():
                path = Path(tmp) / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            return resources.discoverable_buildings(Path(tmp) / "game", Path(tmp) / "mod", {"building_m"})

    GROUPS = ("bg_capped = { capped_by_resources = yes }\n"
              "bg_found = { parent_group = bg_capped discoverable_resource = yes }\n")

    def test_bare_redefinition_in_a_later_file_loses(self):
        got = self.resolve({"game/common/building_groups/00.txt": self.GROUPS,
                            "game/common/buildings/03_mines.txt": "building_m = { building_group = bg_capped }\n",
                            "mod/common/buildings/03_zz.txt": "building_m = { building_group = bg_found }\n"})
        self.assertEqual(got, {"building_m": False})

    def test_inject_and_replace_change_the_group(self):
        base = {"game/common/building_groups/00.txt": self.GROUPS,
                "game/common/buildings/03_mines.txt": "building_m = { building_group = bg_capped }\n"}
        for form in ("INJECT", "REPLACE"):
            got = self.resolve({**base, "mod/common/buildings/03_zz.txt":
                                f"{form}:building_m = {{ building_group = bg_found }}\n"})
            self.assertEqual(got, {"building_m": True}, form)

    def test_mod_group_and_inherited_flag(self):
        got = self.resolve({"game/common/building_groups/00.txt": self.GROUPS,
                            "mod/common/building_groups/x.txt": "REPLACE_OR_CREATE:bg_child = { parent_group = bg_found }\n",
                            "mod/common/buildings/x.txt": "building_m = { building_group = bg_child }\n"})
        self.assertEqual(got, {"building_m": True})


class CommittedMap(unittest.TestCase):
    """The committed copies alone (no game)."""

    @classmethod
    def setUpClass(cls):
        cls.states = read_states(REGIONS)

    def test_no_province_in_two_states(self):
        owner = {}
        for name, state in self.states.items():
            for province in state["provinces"]:
                self.assertNotIn(province, owner, f"{province} in {owner.get(province)} and {name}")
                owner[province] = name

    def test_config_keys_name_committed_states(self):
        deposits = json.loads((ROOT / "deposits_config.json").read_text(encoding="utf-8"))
        traits = resources.load_trait_mapping(ROOT / "state_trait_config.json")
        stale = sorted(k for k in [*deposits, *traits] if k not in self.states)
        self.assertEqual(stale, [], "config keys naming no state region; point them at the successor")

    def test_every_land_state_has_an_id(self):
        self.assertEqual([k for k, s in self.states.items() if s["id"] is None], [])


@unittest.skipUnless(HAVE_GAME, "needs the Victoria 3 install (map_data/state_regions)")
class AgainstVanilla(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vanilla = read_states(VANILLA_REGIONS)
        cls.mod = read_states(REGIONS)

    def test_same_files(self):
        self.assertEqual(sorted(p.name for p in REGIONS.glob("*.txt")),
                         sorted(p.name for p in VANILLA_REGIONS.glob("*.txt")))

    def test_same_states(self):
        self.assertEqual(sorted(set(self.mod) - set(self.vanilla)), [], "states vanilla no longer has")
        self.assertEqual(sorted(set(self.vanilla) - set(self.mod)), [], "vanilla states the copies lack")

    def test_vanilla_fields_pass_through(self):
        """ids, provinces, naval exits and both cold fields, a field vanilla leaves out included."""
        for name, state in self.vanilla.items():
            with self.subTest(state=name):
                self.assertEqual(self.mod[name], state)

    def test_copies_are_current(self):
        """A fresh resources.py run (deposits, traits, the deposit rule) writes exactly the committed files."""
        mapping = resources.load_mapping(ROOT / "deposits_config.json")
        traits = resources.load_trait_mapping(ROOT / "state_trait_config.json")
        files = sorted(VANILLA_REGIONS.glob("*.txt"))
        capped = {b for p in files for m in resources.CAPPED_RE.finditer(p.read_text(encoding="utf-8-sig"))
                  for b, _ in resources.CAPPED_ENTRY_RE.findall(m.group(2))}
        discoverable = resources.discoverable_buildings(GAME, ROOT, set(resources.SUBGOOD_TO_BGTYPE.values()) | capped)
        with tempfile.TemporaryDirectory() as tmp:
            for path in files:
                out = Path(tmp) / path.name
                resources.process_file(path, out, mapping, trait_mapping=traits, verbose=False,
                                       discoverable=discoverable)
                with self.subTest(file=path.name):
                    self.assertEqual(out.read_bytes(), (REGIONS / path.name).read_bytes(),
                                     "stale: run python3 resources.py")


if __name__ == "__main__":
    unittest.main()
