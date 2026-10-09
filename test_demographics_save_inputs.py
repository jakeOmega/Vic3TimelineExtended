"""scripts/analysis/demographics_save_inputs.py reads pops, owners, laws and technology."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_save_inputs as S  # noqa: E402

SLICE = ROOT / "test_fixtures" / "demographics" / "gb_1836_slice.v3"

TINY = """SAV0100tiny
meta_data={
\tversion="1.14.5"
}
pops={
\tdatabase={
7={
\ttype=aristocrats
\tworkforce=100
\tdependents=300
\tlocation=1
\tnum_literate=50
\twealth=30
\tprevious_quality_of_life=28
\tweekly_budget={ 0 0 1 }
\tfood_security={
\t\ttype=not_a_pop_type
\t}
\tsocial_class={
\t\tsocial_class=upper_class
\t}
}
8={
\ttype=peasants
\tlocation=1
\twealth=5
}
\t}
}
country_manager={
\tdatabase={
3={
\tdefinition="TST"
\tbudget={
\t\tweekly_expenses={ 0 0 }
\t}
}
\t}
}
states={
\tdatabase={
1={
\tcountry=3
}
\t}
}
laws={
\tdatabase={
0={
\tlaw=law_serfdom
\tcountry=3
\tactive=yes
}
1={
\tlaw=law_homesteading
\tcountry=3
}
\t}
}
technology={
\tdatabase={
0={
\tcountry=3
\tacquired_technologies={ enclosure railways }
}
\t}
}
"""


class TestTinySave(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile("w", suffix=".v3", delete=False, encoding="utf-8")
        self.tmp.write(TINY)
        self.tmp.close()
        self.sections = S.read_sections(self.tmp.name)

    def tearDown(self):
        Path(self.tmp.name).unlink()

    def test_fields_one_tab_in_only(self):
        pop = self.sections["pops"]["7"]
        self.assertEqual(pop["type"], "aristocrats")
        self.assertEqual(pop["social_class"], "upper_class")

    def test_country_inputs(self):
        c = S.country_inputs(self.sections)["TST"]
        self.assertEqual(c.population, 400)
        self.assertAlmostEqual(c.sol, 28)
        self.assertAlmostEqual(c.literacy, 0.5)
        self.assertEqual(c.laws, {"law_serfdom"})
        self.assertEqual(c.techs, {"enclosure", "railways"})
        self.assertEqual(dict(c.strata_people), {"upper": 400})

    def test_empty_pop_is_skipped(self):
        c = S.country_inputs(self.sections)["TST"]
        self.assertEqual(c.rural, 0)


@unittest.skipUnless(SLICE.exists(), "fixture written in Task 3 Step 4")
class TestSlice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = S.country_inputs(S.read_sections(SLICE))

    def test_britain_and_portugal(self):
        self.assertEqual(set(self.inputs), {"GBR", "POR"})
        gbr = self.inputs["GBR"]
        self.assertEqual(gbr.states, 26)
        self.assertGreater(gbr.population, 1_000_000)
        self.assertTrue({"law_women_own_property", "law_tenant_farmers", "law_charitable_health_system"} <= gbr.laws)
        self.assertIn("law_no_womens_rights", self.inputs["POR"].laws)
        self.assertIn("enclosure", gbr.techs)
        self.assertLessEqual(set(gbr.strata_people), {"lower", "middle", "upper"})
        self.assertTrue(0 < gbr.literacy < 1 and 0 < gbr.urban_share < 1)
