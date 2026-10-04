"""Numerical climate regressions against the committed script-value AST."""

import copy
from decimal import Decimal
from pathlib import Path
import unittest

import household_emissions as household
import pm_emissions as emissions
from test_building_emissions import parsed, body, scalar, state_scaled, workforce

ROOT = Path(__file__).resolve().parent
D = Decimal


class Values:
    """Evaluate the arithmetic/scoping/curve subset used by these climate values.

    Engine-supplied state totals and the market leader's cut are fixture inputs;
    policy arithmetic and household interpolation come from production script.
    """

    def __init__(self):
        self.data = {}
        for path in ("common/script_values/extra_script_values.txt",
                     "common/script_values/greenhouse_gas_factors.txt",
                     "common/script_values/household_emissions_values.txt",
                     household.OUTPUT):
            self.data.update(parsed(path))

    def value(self, item, scope):
        item = emissions.unwrap(item)
        if isinstance(item, dict):
            return self.block(item, scope)
        if item in scope:
            return D(scope[item])
        if item in self.data:
            return self.value(self.data[item], scope)
        return D(item)

    def condition(self, block, scope):
        for name, (op, rhs) in block.items():
            if name == "NOT":
                if self.condition(rhs, scope):
                    return False
                continue
            if name == "is_pop_type":
                if scope["pop_type"] != rhs:
                    return False
                continue
            left, right = self.value(name, scope), self.value(rhs, scope)
            if not {"<": left < right, "<=": left <= right, ">": left > right,
                    ">=": left >= right, "=": left == right}[op]:
                return False
        return True

    def block(self, block, scope, total=D(0)):
        chosen = False
        for key, values in block.items():
            for raw in values if isinstance(values, list) else [values]:
                arg = emissions.unwrap(raw)
                if key in ("if", "else_if", "else"):
                    if key == "if":
                        chosen = False
                    if not chosen and (key == "else" or self.condition(body(arg, "limit"), scope)):
                        total = self.block({k: v for k, v in arg.items() if k != "limit"}, scope, total)
                        chosen = True
                elif key == "every_scope_pop":
                    for pop in scope["pops"]:
                        if "limit" not in arg or self.condition(body(arg, "limit"), pop):
                            total = self.block({k: v for k, v in arg.items() if k != "limit"}, pop, total)
                elif key in ("owner", "market") or key.startswith("mg:"):
                    total = self.block(arg, scope[key], total)
                else:
                    value = self.value(arg, scope)
                    if key == "value":
                        total = value
                    elif key == "add":
                        total += value
                    elif key == "subtract":
                        total -= value
                    elif key == "multiply":
                        total *= value
                    elif key == "divide":
                        total /= value
                    elif key == "min":
                        total = max(total, value)
                    elif key == "max":
                        total = min(total, value)
                    else:
                        raise AssertionError(f"Unsupported operation: {key}")
        return total


def state(*, population=0, wealth=20, industry=5, removal=0, industry_cut=1, household_cut=0, peasants=0, supply=None):
    supply = supply if supply is not None else dict.fromkeys(("wood", "fabric", "coal", "oil", "electricity"), 1)
    market = {f"mg:{good}": {"market_goods_sell_orders": supply.get(good, 0)} for good in ("wood", "fabric", "coal", "oil", "electricity")}
    return {"state_population": population, "average_sol": wealth,
            "pops": [{"total_size": D(population) * (1-D(peasants)), "pop_type": "laborers"},
                     {"total_size": D(population) * D(peasants), "pop_type": "peasants"}],
            f"modifier:{emissions.STATE_MODIFIER}": industry,
            f"modifier:{emissions.ATMOSPHERIC_MODIFIER}": removal,
            "owner": {"market": market, "gw_emission_multiplier_script_value": industry_cut,
                      "modifier:country_household_greenhouse_gas_emissions_mult": household_cut}}


class HouseholdEmissionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = emissions.load_state(ROOT)
        cls.values = Values()

    def test_generated_curve_matches_every_buy_package_and_interpolates(self):
        points = household.heating_curve(self.graph)
        for level, heating in points:
            self.assertEqual(self.values.value("gw_household_heating_budget", state(wealth=level)), heating)
        for (level, heating), (_, next_heating) in zip(points, points[1:]):
            self.assertEqual(self.values.value("gw_household_heating_budget", state(wealth=D(level)+D("0.5"))),
                             (heating + next_heating) / 2)
        self.assertEqual(self.values.value("gw_household_heating_budget", state(wealth=0)), points[0][1])
        self.assertEqual(self.values.value("gw_household_heating_budget", state(wealth=1000)), points[-1][1])

    def test_curve_changes_with_packages_and_rejects_invalid_demand(self):
        graph = copy.copy(self.graph)
        graph.mod_parsers = dict(self.graph.mod_parsers)
        graph.mod_parsers["Buy Packages"] = copy.copy(self.graph.mod_parsers["Buy Packages"])
        graph.mod_parsers["Buy Packages"].data = copy.deepcopy(graph.mod_parsers["Buy Packages"].data)
        goods = body(emissions.unwrap(graph.mod_parsers["Buy Packages"].data["wealth_20"]), "goods")
        goods["popneed_heating"] = ("=", "99")
        self.assertEqual(household.heating_curve(graph)[19], (20, D(99)))
        self.assertIn("value = 99", household.plan_outputs(graph)[household.OUTPUT])
        for bad in ("-1", "NaN", "Infinity"):
            goods["popneed_heating"] = ("=", bad)
            with self.assertRaises(ValueError):
                household.plan_outputs(graph)

    def test_population_and_baseline_consumption_units(self):
        baseline = self.values.value("gw_state_household_greenhouse_gas_emissions", state(population=10000, wealth=1))
        expected = D(15) * D("0.625") * (D(2) / 9 / 30 * 2 + D(3) / 9 / 40 * D("1.74")) / 10000
        self.assertAlmostEqual(baseline, expected, places=20)
        self.assertAlmostEqual(self.values.value("gw_state_household_greenhouse_gas_emissions", state(population=20000, wealth=1)), baseline * 2, places=20)
        self.assertEqual(self.values.value("gw_state_household_greenhouse_gas_emissions", state(population=0)), 0)

    def test_household_supply_and_subsistence_calibration(self):
        evaluate = lambda **kw: self.values.value("gw_state_household_greenhouse_gas_emissions", state(population=1000000, **kw))
        self.assertEqual(evaluate(supply={"wood": 100, "fabric": 50}), 0)
        self.assertEqual(self.values.value("gw_household_oil_heating_share", state(supply={"coal": 100, "wood": 100})), 0)
        baseline = evaluate()
        self.assertAlmostEqual(evaluate(peasants=1), baseline * D("0.05"), places=20)
        self.assertAlmostEqual(evaluate(peasants=D("0.8")), baseline * D("0.24"), places=20)
        self.assertLess(evaluate(supply={"coal": 1, "oil": 1, "electricity": 100}), baseline)
        self.assertEqual(evaluate(supply={}), 0)
        self.assertEqual(self.values.value("gw_household_coal_heating_share", state(supply={"coal": 100})), D("0.8"))

    def test_three_policies_eliminate_household_emissions_without_negative_burn(self):
        modifiers = parsed("common/static_modifiers/extra_modifiers.txt")
        cuts = {name: scalar(body(modifiers, name), "country_household_greenhouse_gas_emissions_mult")
                for name in ("green_building_codes_modifier", "renewable_investment_modifier", "fossil_fuel_divestment_modifier")}
        self.assertEqual(cuts["green_building_codes_modifier"], D("-0.60"))
        self.assertEqual(sum(cuts.values()), -1)
        baseline = self.values.value("gw_state_household_greenhouse_gas_emissions", state(population=1000000))
        codes = self.values.value("gw_state_household_greenhouse_gas_emissions", state(population=1000000, household_cut=cuts["green_building_codes_modifier"]))
        self.assertEqual(codes, baseline * D("0.4"))
        for cut in (sum(cuts.values()), D("-1.2")):
            self.assertEqual(self.values.value("gw_state_household_greenhouse_gas_emissions", state(population=1000000, household_cut=cut)), 0)

    def test_national_household_policy_does_not_change_neighbors_or_industry(self):
        own = state(population=1000000, household_cut=D("-0.6"), industry=0)
        other = state(population=1000000, industry=0)
        self.assertEqual(self.values.value("gw_state_greenhouse_gas_emissions", own),
                         self.values.value("gw_state_greenhouse_gas_emissions", other) * D("0.4"))
        self.assertEqual(self.values.value("gw_state_greenhouse_gas_emissions", state(household_cut=-1)), D("0.005"))

    def test_warming_follows_building_net_values_and_preserves_full_removal(self):
        no_capture = self.values.value("gw_state_greenhouse_gas_emissions", state(industry=5))
        tier_two = self.values.value("gw_state_greenhouse_gas_emissions", state(industry=D("2.5")))
        self.assertEqual(tier_two, no_capture / 2)
        with_policy = self.values.value("gw_state_greenhouse_gas_emissions", state(industry=D("2.5"), industry_cut=D("0.55")))
        self.assertEqual(with_policy, D("0.001375"))
        with_removal = self.values.value("gw_state_greenhouse_gas_emissions", state(industry=D("2.5"), industry_cut=D("0.55"), removal=168))
        self.assertEqual(with_removal, with_policy - D("0.168"))
        self.assertLess(with_removal, 0)

    def test_source_capture_only_cannot_turn_industry_into_atmospheric_removal(self):
        self.assertGreaterEqual(self.values.value("gw_state_greenhouse_gas_emissions", state(industry=D("1.25"), industry_cut=0)), 0)
        self.assertEqual(self.values.value("gw_state_greenhouse_gas_emissions", state(industry=D("1.25"), industry_cut=0, removal=168)), D("-0.168"))

    def test_every_fuel_method_carries_its_gross_and_capture_its_cut(self):
        methods = self.graph.mod_parsers["PMs"].data
        checked = 0
        for name, pm in methods.items():
            gross = emissions.recipe_emissions(pm, {"coal": D(2), "oil": D("1.74")},
                                               netted=emissions.netted_fuel(name, pm))
            if not gross:
                continue
            checked += 1
            if name not in emissions.SYNTHETIC_CREDITS:  # net of the output credit; checked below
                self.assertEqual(scalar(state_scaled(pm), emissions.STATE_MODIFIER), gross, name)
        self.assertEqual(checked, 248)
        for name, pm in parsed("common/production_methods/carbon_capture_generated_pms.txt").items():
            if "state_modifiers" in emissions.unwrap(pm):
                self.assertLess(scalar(state_scaled(pm), emissions.STATE_MODIFIER), 0, name)

    def test_synthetic_credits_scale_with_industry_and_do_not_create_removal(self):
        for name, fuel in emissions.SYNTHETIC_CREDITS.items():
            pm = emissions.unwrap(self.graph.mod_parsers["PMs"].data[name])
            mirror = body(body(pm, "state_modifiers"), "workforce_scaled")
            net = scalar(mirror, emissions.STATE_MODIFIER)
            self.assertNotIn(emissions.ATMOSPHERIC_MODIFIER, mirror)
            burn = scalar(workforce(pm), f"goods_output_{fuel}_add") * D({"coal": "2", "oil": "1.74"}[fuel]) / 10
            self.assertEqual(net, emissions.recipe_emissions(pm, {"coal": D(2), "oil": D("1.74")}) - burn)
            self.assertNotIn("state_carbon_capture_add", mirror)
            for multiplier in (D(1), D("0.5"), D("0.25"), D(0)):
                self.assertEqual(self.values.value("gw_state_greenhouse_gas_emissions", state(industry=net, industry_cut=multiplier)), net * multiplier / 1000)
                chain = self.values.value("gw_state_greenhouse_gas_emissions", state(industry=net+burn, industry_cut=multiplier))
                gross = emissions.recipe_emissions(pm, {"coal": D(2), "oil": D("1.74")})
                self.assertEqual(chain, gross * multiplier / 1000)
                self.assertGreaterEqual(chain, 0)
        factors = parsed(emissions.FACTORS)
        for name, (fuel, parameter) in emissions.REMOVALS.items():
            pm = emissions.unwrap(self.graph.mod_parsers["PMs"].data[name])
            mirror = body(body(pm, "state_modifiers"), "workforce_scaled")
            capacity = scalar(factors, parameter) * scalar(factors, f"gw_emission_factor_{fuel}") / 10
            self.assertEqual(scalar(mirror, emissions.ATMOSPHERIC_MODIFIER), capacity)
            self.assertNotIn(emissions.STATE_MODIFIER, mirror)

    def test_removal_policy_throughput_is_registered_and_state_types_have_localization(self):
        types = parsed("common/modifier_type_definitions/mod_entity_modifier_types.txt")
        self.assertIn("building_synthetics_plant_coal_throughput_add", types)
        loc = "\n".join(p.read_text(encoding="utf-8-sig") for p in (ROOT / "localization/english").glob("*.yml"))
        for modifier in (emissions.STATE_MODIFIER, emissions.ATMOSPHERIC_MODIFIER):
            self.assertIn(f" {modifier}:0 ", loc)
            self.assertIn(f" {modifier}_desc:0 ", loc)

    def test_synthetic_export_negative_accounting_is_not_atmospheric_removal(self):
        producer = self.values.value("gw_state_greenhouse_gas_emissions", state(industry=-168))
        importer = self.values.value("gw_state_greenhouse_gas_emissions", state(industry=168))
        self.assertLess(producer, 0)
        self.assertEqual(producer + importer, 0)
        for key in ("gw_emis_capture_tt_ours", "gw_emis_capture_tt_theirs"):
            line = next(line for line in (ROOT / "localization/english/te_miscellaneous_l_english.yml").read_text(encoding="utf-8-sig").splitlines() if line.startswith(f" {key}:"))
            self.assertIn("Exporting synthetic fuels", line)
            self.assertNotIn("only way", line)

    def test_dac_goods_cost_exceeds_representative_tier_two_source_capture(self):
        methods = self.graph.mod_parsers["PMs"].data
        goods = self.graph.mod_parsers["Goods"].data
        def cost_per_unit(name):
            recipe = workforce(methods[name])
            cost = D(0)
            for key, amount in recipe.items():
                if key.startswith("goods_input_") and key.endswith("_add"):
                    good = key[len("goods_input_"):-len("_add")]
                    cost += D(emissions.unwrap(amount)) * scalar(emissions.unwrap(goods[good]), "cost")
                if key == "goods_output_electricity_add":
                    cost -= D(emissions.unwrap(amount)) * scalar(emissions.unwrap(goods["electricity"]), "cost")
            mirror = state_scaled(methods[name])
            if emissions.ATMOSPHERIC_MODIFIER in mirror:
                return cost / scalar(mirror, emissions.ATMOSPHERIC_MODIFIER)
            return cost / -scalar(mirror, emissions.STATE_MODIFIER)
        self.assertGreater(cost_per_unit("pm_direct_air_capture"), cost_per_unit("pm_carbon_capture_2_base_building_power_plant_coal25_oil0"))

    def test_ownership_updates_preserve_other_state_blocks_and_remove_stale_mirrors(self):
        block = 'pm_test = {\n\tstate_modifiers = {\n\t\tunscaled = { state_pollution_generation_add = 2 }\n\t}\n}\n'
        changed = emissions._with_state_modifier(block, D(5), modifier=emissions.STATE_MODIFIER)
        self.assertIn("state_pollution_generation_add = 2", changed)
        self.assertEqual(emissions._with_state_modifier(changed, D(5), modifier=emissions.STATE_MODIFIER), changed)
        self.assertNotIn(emissions.STATE_MODIFIER, emissions._with_state_modifier(changed, D(0), modifier=emissions.STATE_MODIFIER))

    def test_generated_output_is_current(self):
        self.assertEqual((ROOT / household.OUTPUT).read_text(encoding="utf-8-sig"), household.plan_outputs(self.graph)[household.OUTPUT])


if __name__ == "__main__":
    unittest.main()
