"""Regime change thresholds on the mod's law groups follow vanilla's by category.

Since 1.15.2 a law group carries `regime_change_min_progressiveness_difference`:
a regime change imposes the holder's law in that group only when the two laws'
progressiveness differs by at least that much. Vanilla gives its power structure
groups 50 (the old global define), its economic system and trade policy 25 and
labour associations 75. The mod's economy groups take vanilla's economy value
and its other groups the old 50 (docs/audits/vanilla_1_15_2_migration.md).

A wrong number logs nothing: it only decides which laws a regime change takes
along. No game install needed.
"""

import unittest

import vanilla_parsed
from test_tax_code_rule import load, plain

GROUPS = "common/law_groups/extra_law_groups.txt"
FIELD = "regime_change_min_progressiveness_difference"

ECONOMY_GROUPS = {
    "lawgroup_antitrust",
    "lawgroup_financial_regulation",
    "lawgroup_genetic_rights",
    "lawgroup_intellectual_property",
    "lawgroup_monetary_policy",
    "lawgroup_right_to_information",
}
# The old define, which 1.15.2 moved onto each group.
OLD_DEFINE = "50"


def carried(groups):
    """{group: (category, threshold)} for the groups a regime change can impose."""
    return {name: (body.get("law_group_category"), body[FIELD])
            for name, body in groups.items() if body.get(FIELD, "0") != "0"}


class RegimeChangeThresholdsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vanilla = carried(plain(vanilla_parsed.load().data["Law Groups"]))
        cls.mod = carried(load(GROUPS))

    def vanilla_value(self, category):
        values = {t for c, t in self.vanilla.values() if c == category}
        self.assertEqual(len(values), 1, f"vanilla's {category} groups no longer share one "
                         f"threshold ({sorted(values)}): choose the mod's again")
        return values.pop()

    def test_economy_groups_take_vanillas_economy_threshold(self):
        expected = self.vanilla_value("economy")
        economy = {n for n, (c, _) in self.mod.items() if c == "economy"}
        self.assertEqual(economy, ECONOMY_GROUPS)
        for name in sorted(economy):
            with self.subTest(group=name):
                self.assertEqual(self.mod[name][1], expected)

    def test_power_structure_groups_take_vanillas_power_structure_threshold(self):
        expected = self.vanilla_value("power_structure")
        self.assertEqual(expected, OLD_DEFINE)
        for name, (category, threshold) in sorted(self.mod.items()):
            if category == "power_structure":
                with self.subTest(group=name):
                    self.assertEqual(threshold, expected)

    def test_human_rights_groups_keep_the_old_define(self):
        # Vanilla's one human rights group with a threshold is labour associations at
        # 75, a choice for that group's spread (Factory Councils at 125), not a rule
        # for the category.
        for name, (category, threshold) in sorted(self.mod.items()):
            if category == "human_rights":
                with self.subTest(group=name):
                    self.assertEqual(threshold, OLD_DEFINE)

    def test_the_nineteen_groups_carried_before_1_15_2_still_are(self):
        self.assertEqual(len(self.mod), 19, sorted(self.mod))


if __name__ == "__main__":
    unittest.main()
