"""scripts/analysis/demographics_save_inputs.py reads pops, owners, laws and technology."""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
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
\tincorporation=1
}
2={
\tcountry=3
\tincorporation=0.4
}
\t}
}
institutions={
\tdatabase={
16777220={
\tinstitution=institution_health_system
\tinvestment=3
\tgrowth=0.6205
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

    def test_institutions_and_incorporation(self):
        c = S.country_inputs(self.sections)["TST"]
        self.assertEqual(c.institutions, {"institution_health_system": 3})
        self.assertEqual(c.incorporated_people, 400)
        self.assertAlmostEqual(c.incorporated_share, 1.0)

    def test_a_state_still_incorporating_is_not_incorporated(self):
        text = TINY.replace("8={\n\ttype=peasants\n\tlocation=1\n",
                            "9={\n\ttype=peasants\n\tworkforce=60\n\tdependents=40\n\tlocation=2\n}\n"
                            "8={\n\ttype=peasants\n\tlocation=1\n", 1)
        self.assertNotEqual(text, TINY)
        with tempfile.NamedTemporaryFile("w", suffix=".v3", delete=False, encoding="utf-8") as fh:
            fh.write(text)
        try:
            c = S.country_inputs(S.read_sections(fh.name))["TST"]
        finally:
            Path(fh.name).unlink()
        self.assertEqual(c.population, 500)
        self.assertEqual(c.incorporated_people, 400)
        self.assertAlmostEqual(c.incorporated_share, 0.8)

    def test_empty_pop_is_skipped(self):
        c = S.country_inputs(self.sections)["TST"]
        self.assertEqual(c.rural, 0)


class TestWealthTerm(unittest.TestCase):
    """The game averages the wealth term over the pops (Inputs.wealth_tfr); the mean SoL's curve is not that."""

    EXTRA = """9={
\ttype=laborers
\tworkforce=100
\tdependents=100
\tlocation=1
\tprevious_quality_of_life=0
}
10={
\ttype=laborers
\tworkforce=100
\tdependents=100
\tlocation=1
\tprevious_quality_of_life=16
}
"""

    def inputs(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "save.v3"
            path.write_text(text, encoding="utf-8")
            return S.country_inputs(S.read_sections(path))["TST"]

    def test_wealth_tfr_is_the_pop_weighted_curve(self):
        c = self.inputs(TINY.replace("8={\n\ttype=peasants", self.EXTRA + "8={\n\ttype=peasants"))
        self.assertEqual(c.population, 800)
        self.assertAlmostEqual(c.sol, 18)                       # (28 x 400 + 0 x 200 + 16 x 200) / 800
        by_pop = (M.wealth_tfr(28) * 400 + M.wealth_tfr(0) * 200 + M.wealth_tfr(16) * 200) / 800
        self.assertAlmostEqual(c.wealth_tfr, by_pop)
        self.assertAlmostEqual(c.wealth_tfr, 5.0)
        self.assertLess(c.wealth_tfr, M.wealth_tfr(c.sol) - 0.1)   # the curve at the mean, 5.2, is higher

    def test_one_pop_is_the_curve_at_its_sol(self):
        c = self.inputs(TINY)
        self.assertAlmostEqual(c.wealth_tfr, M.wealth_tfr(28))

    def test_a_country_with_no_people_has_no_wealth_term(self):
        self.assertIsNone(S.CountryInputs("EMP").wealth_tfr)


class TestNotPlainText(unittest.TestCase):
    """A binary or zipped save must stop the reader, not read as an empty save."""

    def read(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "autosave.v3"
            path.write_bytes(data)
            with self.assertRaises(ValueError) as cm:
                S.read_sections(path)
            return str(cm.exception)

    def test_zip_header_raises_naming_the_file(self):
        msg = self.read(b"SAV01036\nPK\x03\x04\x14\x00\x00\x00\x08\x00\xff\x00pops={\n")
        self.assertIn("autosave.v3", msg)
        self.assertIn("meta_data={", msg)

    def test_binary_second_line_raises(self):
        self.assertIn("autosave.v3", self.read(b"SAV0103\n\xffU\x01\x00\x03\x00\x8f\x05pops={\n\tdatabase={\n"))

    def test_one_line_file_raises(self):
        self.read(b"SAV0100only\n")
        self.read(b"")

    def test_plain_text_with_windows_line_ends_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plain.v3"
            path.write_bytes(TINY.replace("\n", "\r\n").encode("utf-8"))
            self.assertIn("7", S.read_sections(path)["pops"])

    def test_cli_reports_it_and_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "autosave.v3"
            path.write_bytes(b"SAV0103\nPK\x03\x04\x00\x00")
            err = io.StringIO()
            with redirect_stderr(err):
                self.assertEqual(S.main(["summary", str(path)]), 1)
            self.assertIn("autosave.v3", err.getvalue())


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
