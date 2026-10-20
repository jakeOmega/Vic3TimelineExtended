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
state_region_manager={
\tdatabase={
0={
\ttemplate=STATE_TEST
\tarable_land=40
\tpollution=127.5
\ttraits={ state_trait_natural_harbors }
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

    def test_state_pollution(self):
        """Each state's region's pollution (0 to POLLUTION_MAX), for predict's Pollution Impact line (owner,
        2026-10-11). A state with no region in the save has none."""
        self.assertEqual(S.state_pollution(self.sections), {})
        text = TINY.replace("\tcountry=3\n\tincorporation=1\n}", "\tcountry=3\n\tincorporation=1\n\tregion=\"STATE_TEST\"\n}", 1)
        self.assertIn('region="STATE_TEST"', text)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "polluted.v3"
            path.write_text(text, encoding="utf-8")
            self.assertEqual(S.state_pollution(S.read_sections(str(path))), {"1": 127.5})

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

    def test_state_inputs_split_the_country_by_state(self):
        # the census works state by state: each state's own pops, the owner's laws, techs and institutions
        text = TINY.replace("8={\n\ttype=peasants\n\tlocation=1\n",
                            "9={\n\ttype=peasants\n\tworkforce=60\n\tdependents=40\n\tlocation=2\n}\n"
                            "8={\n\ttype=peasants\n\tlocation=1\n", 1)
        with tempfile.NamedTemporaryFile("w", suffix=".v3", delete=False, encoding="utf-8") as fh:
            fh.write(text)
        try:
            states = S.state_inputs(S.read_sections(fh.name))["TST"]
        finally:
            Path(fh.name).unlink()
        by_id = {sid: (st, inc) for sid, st, inc in states}
        self.assertEqual(set(by_id), {"1", "2"})
        self.assertEqual((by_id["1"][0].population, by_id["2"][0].population), (400, 100))
        self.assertEqual((by_id["1"][1], by_id["2"][1]), (True, False), "state 2 is still incorporating")
        for st, _ in by_id.values():
            self.assertEqual(st.laws, {"law_serfdom"})
            self.assertEqual(st.institutions, {"institution_health_system": 3})

    def test_agrarian_share_counts_peasants_and_farmers(self):
        # the walk's te_dg_agr_share (Late Marriage's inheritance driver): Peasants and Farmers, not Slaves
        c = S.CountryInputs("TST")
        for kind, size in (("peasants", 300.0), ("farmers", 100.0), ("slaves", 200.0), ("laborers", 400.0)):
            S._add_pop(c, {"type": kind}, size, True)
        self.assertAlmostEqual(c.agrarian_share, 0.4)
        self.assertEqual(S.CountryInputs("EMPTY").agrarian_share, 0.0)

    def test_state_unemployment_counts_the_workforce_with_no_workplace(self):
        """Phase 2 step 4's stand-in for state_unemployment_rate: TINY's aristocrats have no workplace; its peasants
        no workforce."""
        self.assertEqual(S.state_unemployment(self.sections), {"1": (100.0, 100.0)})

    def test_state_regions(self):
        sections = {"states": {"1": {"region": '"STATE_TEST"'}, "2": {}}}
        self.assertEqual(S.state_regions(sections), {"1": "STATE_TEST"})

    def test_family_limitation_is_read_from_the_countrys_timed_modifiers(self):
        # the census reads it through state_fertility_means_add; the harness needs it from the save (#852's
        # deferred minor: France read from a save had 0.6 less means than in game)
        block = ("\ttimed_modifiers={\n\t\tmodifiers={ {\n\t\t\t\tid=1\n\t\t\t\tmodifier=te_demog_family_limitation\n"
                 "\t\t\t\tstart_date=1836.1.1\n\t\t\t} {\n\t\t\t\tid=2\n\t\t\t\tmodifier=te_demog_family_limitation\n"
                 "\t\t\t\tmultiplier=0.5\n\t\t\t\tstart_date=1836.1.1\n\t\t\t} }\n\t}\n")
        text = TINY.replace('3={\n\tdefinition="TST"\n', '3={\n\tdefinition="TST"\n' + block, 1)
        self.assertNotEqual(text, TINY)
        with tempfile.NamedTemporaryFile("w", suffix=".v3", delete=False, encoding="utf-8") as fh:
            fh.write(text)
        try:
            sections = S.read_sections(fh.name)
            c = S.country_inputs(sections)["TST"]
            states = S.state_inputs(sections)["TST"]
        finally:
            Path(fh.name).unlink()
        self.assertAlmostEqual(c.means_add, 1.5 * M.P.FAMILY_LIMITATION_MEANS, msg="each copy at its multiplier")
        for _sid, st, _inc in states:
            self.assertAlmostEqual(st.means_add, c.means_add)
        self.assertEqual(S.country_inputs(self.sections)["TST"].means_add, 0.0)

    def test_a_state_with_migration_crowding_is_crowded(self):
        # the census raises infection deaths by the state's migration penalty from crowding, 0.1 x the modifier's
        # multiplier (te_demog_mult_infection); the save lists it among the state's timed modifiers
        text = TINY.replace("8={\n\ttype=peasants\n\tlocation=1\n",
                            "9={\n\ttype=peasants\n\tworkforce=60\n\tdependents=40\n\tlocation=2\n}\n"
                            "8={\n\ttype=peasants\n\tlocation=1\n", 1)
        text = text.replace("\tincorporation=0.4\n}",
                            "\tincorporation=0.4\n\ttimed_modifiers={\n\t\tmodifiers={ {\n\t\t\t\tid=4\n"
                            "\t\t\t\tmodifier=tourism_output\n\t\t\t\tmultiplier=2\n\t\t\t} {\n\t\t\t\tid=5\n"
                            "\t\t\t\tmodifier=migration_crowding\n\t\t\t\tmultiplier=0.04356\n"
                            "\t\t\t\tstart_date=1836.12.30\n\t\t\t} }\n\t\tnext_id=6\n\t}\n}", 1)
        self.assertIn("modifier=migration_crowding", text)
        with tempfile.NamedTemporaryFile("w", suffix=".v3", delete=False, encoding="utf-8") as fh:
            fh.write(text)
        try:
            states = S.state_inputs(S.read_sections(fh.name))["TST"]
        finally:
            Path(fh.name).unlink()
        by_id = {sid: st for sid, st, _inc in states}
        self.assertAlmostEqual(by_id["2"].crowding, 0.004356)
        self.assertEqual(by_id["1"].crowding, 0.0)

    def test_a_states_malaria_level_is_its_state_regions(self):
        """Calibration step 3: the map files' malaria traits by the state's region; the owner's techs carry the control
        (Malaria Prevention), so the level itself ignores them."""
        text = TINY.replace("\tcountry=3\n\tincorporation=1\n}",
                            "\tcountry=3\n\tincorporation=1\n\tregion=\"STATE_GOLD_COAST\"\n}", 1)
        self.assertIn('region="STATE_GOLD_COAST"', text)
        with tempfile.NamedTemporaryFile("w", suffix=".v3", delete=False, encoding="utf-8") as fh:
            fh.write(text)
        try:
            states = S.state_inputs(S.read_sections(fh.name))["TST"]
        finally:
            Path(fh.name).unlink()
        self.assertEqual({sid: st.malaria for sid, st, _inc in states}, {"1": 1})
        self.assertEqual([st.malaria for _sid, st, _inc in S.state_inputs(self.sections)["TST"]], [0])

    def test_food_security_and_devastation_are_read(self):
        """Phase 2 step 4 (predict): a pop's food security (its nested block's value; the block's other keys are
        not fields) and a state's devastation (0-100 in the save)."""
        text = TINY.replace("\tfood_security={\n\t\ttype=not_a_pop_type\n\t}",
                            "\tfood_security={\n\t\ttype=not_a_pop_type\n\t\tvalue=0.31\n\t\tstarvation=0\n"
                            "\t\tstate=moderate\n\t}", 1)
        text = text.replace("\tcountry=3\n\tincorporation=1\n}", "\tcountry=3\n\tincorporation=1\n\tdevastation=19.5\n}", 1)
        self.assertIn("value=0.31", text)
        self.assertIn("devastation=19.5", text)
        with tempfile.NamedTemporaryFile("w", suffix=".v3", delete=False, encoding="utf-8") as fh:
            fh.write(text)
        try:
            sections = S.read_sections(fh.name)
        finally:
            Path(fh.name).unlink()
        self.assertEqual(sections["pops"]["7"]["food_security"], "0.31")
        self.assertNotIn("food_security", sections["pops"]["8"])
        self.assertEqual(sections["pops"]["7"]["type"], "aristocrats")
        self.assertEqual(sections["states"]["1"]["devastation"], "19.5")

    def test_a_states_timed_modifiers_are_pairs_like_a_countrys(self):
        # one shape for both (review M3)
        text = TINY.replace("\tincorporation=0.4\n}",
                            "\tincorporation=0.4\n\ttimed_modifiers={\n\t\tmodifiers={ {\n\t\t\t\tid=4\n"
                            "\t\t\t\tmodifier=tourism_output\n\t\t\t\tmultiplier=2\n\t\t\t} {\n\t\t\t\tid=5\n"
                            "\t\t\t\tmodifier=migration_crowding\n\t\t\t\tmultiplier=0.04356\n\t\t\t} }\n\t}\n}", 1)
        with tempfile.NamedTemporaryFile("w", suffix=".v3", delete=False, encoding="utf-8") as fh:
            fh.write(text)
        try:
            sections = S.read_sections(fh.name)
        finally:
            Path(fh.name).unlink()
        self.assertEqual(sections["states"]["2"]["timed_modifiers"],
                         [["tourism_output", 2.0], ["migration_crowding", 0.04356]])

    def test_timed_modifiers_are_read_only_inside_their_own_block(self):
        # a country's budget trends carry multiplier= lines and its enactment modifiers modifier= lines at the same
        # depth; neither may touch the timed modifiers, whatever order the save writes the blocks in (review M2)
        block = ("\ttimed_modifiers={\n\t\tmodifiers={ {\n\t\t\t\tid=1\n\t\t\t\tmodifier=te_demog_family_limitation\n"
                 "\t\t\t\tmultiplier=0.5\n\t\t\t} }\n\t}\n"
                 "\ttimed_enactment_modifiers={\n\t\tmodifiers={ {\n\t\t\t\tid=2\n"
                 "\t\t\t\tmodifier=te_demog_family_limitation\n\t\t\t} }\n\t}\n"
                 "\tbudget2={\n\t\tmoney_trend={\n\t\t\tyearly_comp={\n\t\t\t\tmultiplier=9\n\t\t\t}\n\t\t}\n\t}\n")
        text = TINY.replace('3={\n\tdefinition="TST"\n', '3={\n\tdefinition="TST"\n' + block, 1)
        self.assertNotEqual(text, TINY)
        with tempfile.NamedTemporaryFile("w", suffix=".v3", delete=False, encoding="utf-8") as fh:
            fh.write(text)
        try:
            sections = S.read_sections(fh.name)
        finally:
            Path(fh.name).unlink()
        self.assertEqual(sections["country_manager"]["3"]["timed_modifiers"], [["te_demog_family_limitation", 0.5]])
        self.assertAlmostEqual(S.country_inputs(sections)["TST"].means_add, 0.5 * M.P.FAMILY_LIMITATION_MEANS)

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
        self.assertAlmostEqual(c.wealth_tfr, 4.889, places=3)   # WEALTH_TFR_LOW 6.0 (was 5.0 at 6.2)
        self.assertLess(c.wealth_tfr, M.wealth_tfr(c.sol) - 0.1)   # the curve at the mean, 5.07, is higher

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


BUDGETS = """SAV0100tiny
meta_data={
\tversion="1.14.5"
}
country_manager={
\tdatabase={
3={
\tdefinition="TST"
\tbudget={
\t\tweekly_expenses={ 1 2 3 }
\t\tweekly_income={ 10 0 20.5 }
\t}
\tgdp={
\t\tsample_rate=28
\t\tchannels={
0={
\t\t\t\tdate=1953.1.1
\t\t\t\tindex=3
\t\t\t\tvalues={ 100 200 300 0 0 }
\t\t\t}\t\t}
\t}
}
4={
\tdefinition="NOG"
}
\t}
}
"""


class TestCountryBudgets(unittest.TestCase):
    """Phase 2 step 2's pension fit reads each country's revenue and GDP (S.country_budgets)."""

    def test_income_expenses_and_the_latest_gdp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "budgets.v3"
            path.write_text(BUDGETS, encoding="utf-8")
            got = S.country_budgets(path)
        self.assertEqual(set(got), {"TST"}, "a country with no GDP record is left out")
        self.assertEqual(got["TST"], {"gdp": 300.0, "income": 30.5, "expenses": 6.0})


if __name__ == "__main__":
    unittest.main()
