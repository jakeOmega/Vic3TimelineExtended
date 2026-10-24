"""The tech metals mines' equipment ladder is gated like the iron mine's.

pmg_mining_equipment_building_tech_metals_mine has no hand-worked method. Its first
method, the condensing engine pump, is the group's default and fallback, so it carries
no technology (three of the four tech metals mines unlock without watertube_boiler
upstream). Every later pump carries the technology of its iron mine twin; the
high-pressure hydraulic pump had none, so a country could run it on tech metals before
any other mine.
"""
import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
GROUP = "pmg_mining_equipment_building_tech_metals_mine"


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _mod_blocks(text):
    """{name: body} for each unindented `name = {` entry, prefixes dropped."""
    marks = [(m.end(), m.group(1)) for m in re.finditer(r"^(?:[A-Z_]+:)?([\w-]+) = \{", text, re.M)]
    blocks = {}
    for i, (end, name) in enumerate(marks):
        stop = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        blocks[name] = text[end:stop]
    return blocks


class TechMetalsEquipment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod_pms = _mod_blocks(_read("common", "production_methods", "extra_pms.txt"))
        with open(os.path.join(REPO, "vanilla_parsed", "common", "pms.json"), encoding="utf-8") as f:
            cls.vanilla_pms = json.load(f)
        groups = _read("common", "production_method_groups", "extra_pm_groups.txt")
        body = re.search(rf"(?m)^(?:[A-Z_]+:)?{GROUP} = \{{(.*?)^\}}", groups, re.S).group(1)
        listed = re.search(r"production_methods = \{(.*?)\}", body, re.S).group(1)
        cls.methods = re.sub(r"#[^\n]*", "", listed).split()

    def techs(self, pm):
        if pm in self.mod_pms:
            block = re.search(r"unlocking_technologies = \{(.*?)\}", self.mod_pms[pm], re.S)
            return sorted(block.group(1).split()) if block else []
        entry = self.vanilla_pms[pm][1].get("unlocking_technologies")
        if entry is None:
            return []
        value = entry[1]
        return sorted(value if isinstance(value, list) else [value])

    def test_first_method_is_ungated(self):
        self.assertEqual(self.methods[0], "pm_condensing_engine_pump_building_tech_metals_mine")
        self.assertEqual(self.techs(self.methods[0]), [])

    def test_later_methods_match_their_iron_mine_twin(self):
        for pm in self.methods[1:]:
            twin = pm.replace("_building_tech_metals_mine", "_building_iron_mine")
            with self.subTest(pm=pm):
                self.assertTrue(self.techs(pm), f"{pm} has no technology")
                self.assertEqual(self.techs(pm), self.techs(twin))


if __name__ == "__main__":
    unittest.main()
