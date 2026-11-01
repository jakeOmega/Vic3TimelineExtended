"""state_trait_config.json and resources.py's trait step (docs/auto_generated_files.md).

resources.py rebuilds map_data/state_regions/ from vanilla's files, adding the traits the config lists
for each state. An entry written "-state_trait_x" takes vanilla's trait away instead: Fiji and Tonga
lose vanilla's Severe Malaria, since the islands had no malaria (Local Climate design 2026-11-01 § 4).

    python3 test_state_trait_config.py
"""
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "state_trait_config.json"
REGIONS = ROOT / "map_data" / "state_regions"

_spec = importlib.util.spec_from_file_location("resources", ROOT / "resources.py")
resources = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(resources)

BLOCK = ('STATE_X = {\n    id = 1\n    subsistence_building = "building_subsistence_farms"\n'
         '    traits = { "state_trait_a" "state_trait_b" }\n    city = "x1"\n}\n')


def traits_of(state):
    for path in sorted(REGIONS.glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig")
        m = re.search(rf"(?m)^{state} = \{{(.*?)^\}}", text, re.S)
        if m:
            t = re.search(r"traits\s*=\s*\{([^}]*)\}", m.group(1))
            return set(re.findall(r'"([^"]+)"', t.group(1))) if t else set()
    raise AssertionError(f"{state} not in map_data/state_regions")


class TraitStep(unittest.TestCase):
    def test_adds_a_trait(self):
        out = resources.process_traits_block(BLOCK, "STATE_X", {"STATE_X": ["state_trait_c"]})
        self.assertIn('traits = { "state_trait_a" "state_trait_b" "state_trait_c" }', out)

    def test_minus_entry_removes_a_trait(self):
        out = resources.process_traits_block(BLOCK, "STATE_X", {"STATE_X": ["-state_trait_a"]})
        self.assertIn('traits = { "state_trait_b" }', out)
        self.assertNotIn("state_trait_a", out)

    def test_removing_the_last_trait_drops_the_line(self):
        block = BLOCK.replace('"state_trait_a" "state_trait_b"', '"state_trait_a"')
        out = resources.process_traits_block(block, "STATE_X", {"STATE_X": ["-state_trait_a"]})
        self.assertNotIn("traits", out)
        self.assertIn('subsistence_building = "building_subsistence_farms"\n    city = "x1"\n', out)

    def test_removing_an_absent_trait_changes_nothing(self):
        self.assertEqual(resources.process_traits_block(BLOCK, "STATE_X", {"STATE_X": ["-state_trait_z"]}), BLOCK)

    def test_a_removal_never_adds_a_traits_line(self):
        block = BLOCK.replace('    traits = { "state_trait_a" "state_trait_b" }\n', "")
        self.assertEqual(resources.process_traits_block(block, "STATE_X", {"STATE_X": ["-state_trait_a"]}), block)


class Committed(unittest.TestCase):
    def test_islands_without_malaria_lose_the_trait(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        for state in ("STATE_FIJI", "STATE_TONGA"):
            self.assertIn("-state_trait_severe_malaria", config.get(state, []), state)
            self.assertNotIn("state_trait_severe_malaria", traits_of(state), state)

    def test_config_traits_applied(self):
        """Every config entry is reflected in the committed map files: added traits present, removed ones gone."""
        for state, entries in resources.load_trait_mapping(CONFIG).items():
            have = traits_of(state)
            for entry in entries:
                if entry.startswith("-"):
                    self.assertNotIn(entry[1:], have, state)
                else:
                    self.assertIn(entry, have, state)


if __name__ == "__main__":
    unittest.main()
