"""gen_covert_tech_theft: amounts, technology catalog, rendered guards, committed output.

Run: /home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_gen_covert_tech_theft.py
"""

import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
import gen_covert_tech_theft as gen  # noqa: E402

LIVE = gen.Constants(share=Decimal("0.05"), full=Decimal("2"), pri2=Decimal("1.35"), pri3=Decimal("1.6"))


class AmountTest(unittest.TestCase):
    def test_era_7_amounts(self):
        self.assertEqual(gen.amounts(65000, LIVE), [3250, 4388, 5200, 6500, 8775, 10400])

    def test_half_rounds_up(self):
        # 17,500 x 0.05 x 2.7 = 2,362.5
        self.assertEqual(gen.amounts(17500, LIVE)[4], 2363)


class CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = gen.load_state(ROOT)
        cls.catalog = gen.tech_catalog(cls.state)
        cls.by_key = {tech.key: tech for tech in cls.catalog}

    def test_reads_live_constants(self):
        self.assertEqual(gen.read_constants(self.state), LIVE)

    def test_era_costs(self):
        costs = gen.read_era_costs(ROOT)
        self.assertEqual(sorted(costs), list(range(1, 13)))
        self.assertEqual((costs[1], costs[7], costs[12]), (7500, 65000, 2000000))

    def test_categories_and_eras(self):
        self.assertEqual((self.by_key["railways"].category, self.by_key["railways"].era), ("production", 2))
        self.assertEqual((self.by_key["ICBMs"].category, self.by_key["ICBMs"].era), ("military", 7))
        self.assertEqual({tech.era for tech in self.catalog}, set(range(1, 13)))

    def test_excludes_society_and_unresearchable(self):
        self.assertNotIn("mass_media", self.by_key)  # society: no operation steals it
        self.assertNotIn("sericulture", self.by_key)  # can_research = no

    def test_indices_unique_from_one(self):
        self.assertEqual([tech.index for tech in self.catalog], list(range(1, len(self.catalog) + 1)))


if __name__ == "__main__":
    unittest.main()
