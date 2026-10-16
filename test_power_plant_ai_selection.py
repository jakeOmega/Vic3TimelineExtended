"""The AI picks power plants' base method by output, not profit (#933).

Under the default most_profitable the AI moved its power plants down to the
least-loss method whenever their own output pushed the local electricity price
down, and back up when it recovered. Each switch is five years of pm_retooling,
paid by the AI's power-plant subsidy: in a 4x fast run's 1912 save 70% of AI
power plants were retooling and carried 92% of the plants' subsidies. Vanilla
gives the port and railway base groups ai_selection = most_productive; the mod
adds it to the power plant's base group by INJECT.
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GROUP = "pmg_base_building_power_plant"


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(r"^(?:[A-Z_]+:)?" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class TestPowerPlantAiSelection(unittest.TestCase):
    def test_the_base_group_is_most_productive(self):
        groups = _strip_comments(
            (ROOT / "common/production_method_groups/extra_pm_groups.txt").read_text(encoding="utf-8-sig"))
        self.assertRegex(groups, r"(?m)^INJECT:" + GROUP + r"\s*=\s*\{")
        self.assertRegex(_block(groups, GROUP), r"\bai_selection\s*=\s*most_productive\b")

    def test_vanilla_leaves_the_field_to_the_inject(self):
        # The INJECT adds a field vanilla's group doesn't declare. If a vanilla
        # patch sets one, the group carries two and which one the engine keeps
        # is unread: check the patch's value and drop or REPLACE the mod's.
        vanilla = json.loads((ROOT / "vanilla_parsed/common/pm_groups.json").read_text(encoding="utf-8"))
        self.assertNotIn("ai_selection", vanilla[GROUP][1])


if __name__ == "__main__":
    unittest.main()
