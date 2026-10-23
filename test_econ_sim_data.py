"""Mod numbers and sector ladders for the economy growth sim (#1034)."""
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.analysis import econ_sim_data as D

MD = None
MS = None
N = None


def setUpModule():
    global MD, MS, N
    MD = D.load_mod_data()
    MS, N = MD.ms, MD.numbers


class FakeMS:
    """Just enough of ModState for the script-value and number readers."""

    def __init__(self, **categories):
        self.categories = categories

    def get_data(self, name):
        return self.categories[name]


class TestNumbers(unittest.TestCase):
    def test_curve_constants(self):
        # The GDP part +1000% at GBP 100, applying in full at 3% slack and not at all at 15%,
        # moving a third of the way a year (#1034's follow-up).
        self.assertEqual(N.curve, D.CurveConstants(1.0, 1.0, 100.0, 10.0, 0.03, 0.15, 0.33333))
        self.assertTrue(N.curve.has_slack_band)

    def test_historical_curve_is_the_pre_cap_one(self):
        # The curve the c480d386 playthrough ran under (ruling R37): +1000% at GBP 100, no slack part.
        self.assertEqual(D.HISTORICAL_CURVE, D.CurveConstants(1.0, 1.0, 100.0, 10.0))
        self.assertFalse(D.HISTORICAL_CURVE.has_slack_band)

    def test_cost_tiers(self):
        t = N.cost_tiers
        self.assertEqual([t[k] for k in ("construction_cost_very_low", "construction_cost_low", "construction_cost_medium",
                                         "construction_cost_high", "construction_cost_very_high", "construction_cost_super_high",
                                         "construction_cost_mega_high", "construction_cost_extreme")],
                         [100, 200, 400, 600, 800, 2000, 5000, 10000])

    def test_retooling_and_caps(self):
        self.assertEqual((N.retool_mult, N.retool_weeks), (10.0, 260))
        self.assertEqual((N.base_project_cap, N.base_eos_cap), (10.0, 20.0))
        self.assertIn((12, "molecular_assemblers", 200.0), N.project_cap_steps)
        self.assertIn((6, "fluorescent_lamps", 30.0), N.eos_cap_steps)
        self.assertEqual(N.prices["construction"], 1000.0)
        self.assertEqual(N.tech_era["steam_donkey"], 3)

    def test_cap_steps_sorted_by_era(self):
        for steps in (N.project_cap_steps, N.eos_cap_steps):
            self.assertTrue(steps)
            self.assertEqual([s[0] for s in steps], sorted(s[0] for s in steps))

    def test_load_is_fast(self):
        start = time.perf_counter()
        D.load_mod_data()
        self.assertLess(time.perf_counter() - start, 15.0)       # about 2 s on the dev machine; this only catches a blow-up


class TestReaders(unittest.TestCase):
    def test_val_unwraps_pairs(self):
        self.assertEqual(D.val(("=", "5")), "5")
        self.assertEqual(D.val(("=", ("=", "5"))), "5")
        self.assertEqual(D.val(["a", "b"]), ["a", "b"])

    def test_script_number_accepts_plain_and_value_block(self):
        ms = FakeMS(**{"Script Values": {"a": ("=", "5"), "b": ("=", {"value": ("=", "2.5")})}})
        self.assertEqual(D.script_number(ms, "a"), 5.0)
        self.assertEqual(D.script_number(ms, "b"), 2.5)

    def test_script_number_rejects_computed_and_non_numeric(self):
        ms = FakeMS(**{"Script Values": {
            "computed": ("=", {"value": ("=", "1"), "multiply": ("=", "construction_cost_floor_ratio")}),
            "named": ("=", "some_other_value")}})
        with self.assertRaises(ValueError):
            D.script_number(ms, "computed")
        with self.assertRaises(ValueError):
            D.script_number(ms, "named")

    def test_script_number_missing_key_names_it(self):
        with self.assertRaises(KeyError) as ctx:
            D.script_number(FakeMS(**{"Script Values": {}}), "construction_cost_gdppc_reference")
        self.assertIn("construction_cost_gdppc_reference", str(ctx.exception))

    def test_missing_retooling_define_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            defines = Path(tmp) / D.DEFINES_FILE
            defines.parent.mkdir(parents=True)
            defines.write_text("NEconomy = {\n\tMIN_GOODS_PRICE = 1\n}\n", encoding="utf-8")
            with self.assertRaises(KeyError) as ctx:
                D.read_numbers(MS, repo=Path(tmp))
            self.assertIn("RETOOLING_WEEKS", str(ctx.exception))
            defines.write_text("NEconomy = {\n\tRETOOLING_WEEKS = many\n}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                D.read_numbers(MS, repo=Path(tmp))


class TestLadders(unittest.TestCase):
    def test_steam_donkey_breakeven(self):          # engines 1 x 60 + coal -3 x 30 over 1,000 laborers
        tier = D.pm_figures(MS, N, "pm_steam_donkey_building_coal_mine")
        self.assertAlmostEqual(D.breakeven(tier), 0.15)

    def test_dragline_breakeven(self):              # (350 - 180) / 2000
        self.assertAlmostEqual(D.breakeven(D.pm_figures(MS, N, "pm_dragline_excavators_coal_mine")), 0.085)

    def test_crew_only_tier_has_no_breakeven(self):
        self.assertIsNone(D.breakeven(D.PMFigures("x", 12, 0.0, 1000.0, 10.0, 0.0, 0.0)))

    def test_pm_figures_fields(self):
        tier = D.pm_figures(MS, N, "pm_steam_donkey_building_coal_mine")
        self.assertEqual((tier.pm, tier.era, tier.employment, tier.crew), ("pm_steam_donkey_building_coal_mine", 3, -1000.0, 0.0))
        self.assertAlmostEqual(tier.va, tier.goods_out - tier.goods_in)

    def test_base_at_bounds(self):                  # Review Focus 5
        lad = D.ladder(MS, N, "mining")
        self.assertEqual(D.base_at(lad, 0).pm, lad.base[0].pm)
        self.assertEqual(D.base_at(lad, 99).pm, lad.base[-1].pm)

    def test_base_at_picks_the_last_tier_reached(self):
        lad = D.ladder(MS, N, "mining")
        for era in (1, 4, 7, 10):
            got = D.base_at(lad, era)
            self.assertLessEqual(got.era, era)
            later = [t for t in lad.base[lad.base.index(got) + 1:] if t.era <= era]
            self.assertEqual(later, [])

    def test_sector_of(self):
        cases = {"building_wheat_farm": "farming", "building_coal_mine": "mining", "building_food_industry": "light",
                 "building_steel_mill": "heavy", "building_electronic_components_and_semiconductor_industry": "hightech",
                 "building_railway": "infrastructure", "building_power_plant": "infrastructure",
                 "building_construction_sector": "construction", "building_urban_center": "services",
                 "building_subsistence_farms": "peasants", "building_government_administration": "other"}
        for b, s in cases.items():
            self.assertEqual(D.sector_of(MS, b), s, b)

    def test_sector_of_unknown_type_is_other(self):
        self.assertEqual(D.sector_of(MS, "building_not_in_this_version"), "other")

    def test_every_sector_building_maps_to_its_own_sector(self):
        for sector, (building, _, _) in D.SECTOR_BUILDINGS.items():
            self.assertEqual(D.sector_of(MS, building), sector)

    def test_construction_ladder_reads_goods_per_level(self):
        lad = D.ladder(MS, N, "construction")
        self.assertEqual([t.construction_out for t in lad.base][:2], [1.0, 2.0])
        self.assertEqual(lad.base[0].employment, 6000.0)

    def test_maintenance_rates(self):
        self.assertEqual(D.ladder(MS, N, "heavy").maintenance, 0.1)
        self.assertEqual(D.ladder(MS, N, "mining").maintenance, 0.05)
        # Railways pay by their train method (pmg_maintenance_graded)
        rail = D.ladder(MS, N, "infrastructure")
        self.assertEqual(rail.maintenance, 0.05)
        self.assertEqual(D.maintenance_at(rail, "pm_steam_trains"), 0.05)
        self.assertEqual(D.maintenance_at(rail, "pm_electric_trains"), 0.1)
        self.assertEqual(D.maintenance_at(rail, "pm_diesel_trains_principle_transport_3"), 0.1)
        self.assertEqual(D.maintenance_at(rail, "pm_containerized_cargo"), 0.15)
        # a mine's equipment unlocks the rate it already pays
        mining = D.ladder(MS, N, "mining")
        for pm in mining.base:
            self.assertEqual(D.maintenance_at(mining, pm.pm), 0.05)

    def test_ladder_shapes(self):
        self.assertEqual(set(MD.ladders), set(D.SECTOR_BUILDINGS))
        for sector, lad in MD.ladders.items():
            self.assertTrue(lad.base, sector)
            self.assertEqual(bool(lad.automation), D.SECTOR_BUILDINGS[sector][2] is not None, sector)
        self.assertEqual(MD.ladders["mining"].automation[0].pm, "pm_no_steam_automation")

    def test_ladders_skip_power_bloc_principle_pms(self):
        infra = D.ladder(MS, N, "infrastructure")
        self.assertFalse([t.pm for t in infra.base if "_principle_" in t.pm])
        self.assertEqual(D.base_at(infra, 3).pm, "pm_steam_trains")
        self.assertEqual(D.base_at(infra, 4).pm, "pm_electric_trains")
        self.assertEqual(D.base_at(infra, 5).pm, "pm_diesel_trains")
        for lad in MD.ladders.values():
            for tier in lad.base + lad.automation:
                self.assertNotIn("_principle_", tier.pm, lad.sector)

    def test_unknown_sector_raises(self):
        with self.assertRaises(KeyError):
            D.ladder(MS, N, "peasants")


class TestSectorCostPoints(unittest.TestCase):
    def test_level_weighted_mean_within_a_sector(self):
        ms = FakeMS(**{
            "Buildings": {"building_a": ("=", {"building_group": ("=", "bg_mining"), "required_construction": ("=", "tier_lo")}),
                          "building_b": ("=", {"building_group": ("=", "bg_mining"), "required_construction": ("=", "tier_hi")})},
            "Building Groups": {"bg_mining": ("=", {"parent_group": ("=", "bg_extraction")}), "bg_extraction": ("=", {})}})
        numbers = SimpleNamespace(cost_tiers={"tier_lo": 100.0, "tier_hi": 600.0})
        got = D.sector_cost_points(ms, numbers, {"building_a": {"levels": 30}, "building_b": {"levels": 10}})
        self.assertEqual(got, {"mining": (30 * 100 + 10 * 600) / 40})

    def test_building_without_required_construction_is_left_out(self):
        ms = FakeMS(**{
            "Buildings": {"building_a": ("=", {"building_group": ("=", "bg_service")})},
            "Building Groups": {"bg_service": ("=", {})}})
        self.assertEqual(D.sector_cost_points(ms, SimpleNamespace(cost_tiers={}), {"building_a": {"levels": 5}}), {})

    def test_unknown_tier_raises(self):
        ms = FakeMS(**{
            "Buildings": {"building_a": ("=", {"building_group": ("=", "bg_mining"), "required_construction": ("=", "tier_gone")})},
            "Building Groups": {"bg_mining": ("=", {})}})
        with self.assertRaises(KeyError) as ctx:
            D.sector_cost_points(ms, SimpleNamespace(cost_tiers={}), {"building_a": {"levels": 5}})
        self.assertIn("tier_gone", str(ctx.exception))

    def test_sectors_split_and_unknown_types_drop(self):
        types = {"building_coal_mine": {"levels": 4}, "building_food_industry": {"levels": 2},
                 "building_subsistence_farms": {"levels": 99}, "building_not_in_this_version": {"levels": 7}}
        got = D.sector_cost_points(MS, N, types)
        self.assertEqual(got, {"mining": 400.0, "light": 600.0})

    def test_zero_levels_leave_the_sector_out(self):
        self.assertEqual(D.sector_cost_points(MS, N, {"building_coal_mine": {"levels": 0}}), {})


if __name__ == "__main__":
    unittest.main()
