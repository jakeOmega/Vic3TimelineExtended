"""National accounting and tariff lifecycle regressions using production scripts."""
from decimal import Decimal
import json
import unittest
from pathlib import Path

from test_household_emissions import Values, state
from test_tax_code_rule import load

ROOT = Path(__file__).resolve().parent
EFFECTS = "common/scripted_effects/global_warming_effects.txt"
TRIGGERS = "common/scripted_triggers/global_warming_triggers.txt"


class CountryValues(Values):
    def block(self, data, scope, total=Decimal(0)):
        for key, arg in data.items():
            if key in ("every_scope_state", "every_scope_country"):
                for child in scope[key]:
                    total = self.block(arg[1], child, total)
            else:
                total = super().block({key: arg}, scope, total)
        return total


class CountryAccountingTest(unittest.TestCase):
    def test_shared_market_sums_distinct_national_reductions_and_removal(self):
        values = CountryValues()
        countries = []
        for cut, removal in ((Decimal("-0.2"), 0), (Decimal("-0.5"), 1000)):
            province = state(industry=1000, removal=removal)
            del province["owner"]["gw_emission_multiplier_script_value"]
            province["owner"]["modifier:country_greenhouse_gas_emissions_mult"] = cut
            countries.append({"every_scope_state": [province]})
        first, second = [values.value("country_greenhouse_gas_emissions_script_value", c) for c in countries]
        self.assertEqual((first, second), (Decimal("0.8"), Decimal("-0.5")))
        leader = {"market": {"every_scope_country": countries}}
        self.assertEqual(values.value("market_greenhouse_gas_emissions_script_value", leader), first + second)
        # Changing the leader changes no country's contribution or total.
        reversed_market = {"market": {"every_scope_country": list(reversed(countries))}}
        self.assertEqual(values.value("market_greenhouse_gas_emissions_script_value", reversed_market), first + second)

    def test_every_country_contributes_once_and_market_snapshot_does_not_accumulate(self):
        pulse = load("common/on_actions/extra_on_actions.txt")["global_warming_update_on_action"]["effect"]
        national, market = pulse["if"][1:]
        self.assertEqual(national["limit"]["owner.capital"], "THIS")
        self.assertEqual(market["limit"]["owner.market_capital"], "THIS")
        self.assertEqual(national["owner"]["change_global_variable"]["add"], "var:gw_disp_country_emis")
        self.assertEqual(market["owner"], {"gw_snapshot_market_emissions_effect": "yes"})

    def test_national_adoption_repeal_and_treaty_never_modify_market_members(self):
        triggers = load(TRIGGERS)
        effects = load(EFFECTS)
        buttons = load("common/scripted_buttons/global_warming_buttons.txt")
        for policy in ("carbon_tax", "renewable_investment", "emission_standards"):
            for op in ("", "remove_"):
                effect = effects[f"gw_effect_{op}{policy}"]["custom_tooltip"]
                self.assertNotIn("every_country", effect)
                self.assertNotIn("gw_cond_leads_market", str(triggers[f"gw_possible_{op}{policy}"]))
                self.assertNotIn("market_capital.owner", str(buttons[f"gw_{op}{policy}_button"]["visible"]))
        treaty = load("common/treaty_articles/109_enforce_emissions_reduction.txt")["enforce_emissions_reduction"]
        self.assertNotIn("market_capital.owner", str(treaty["possible"]) + str(treaty["visible"]))
        self.assertNotIn("every_country", str(treaty["on_entry_into_force"]))


class NativeTariffPolicyTest(unittest.TestCase):
    def test_all_four_native_rate_types_are_registered_and_localized(self):
        definitions = load("common/modifier_type_definitions/global_warming_tariff_modifier_types.txt")
        modifier = load("common/static_modifiers/extra_modifiers.txt")["fossil_fuel_tariffs_modifier"]
        expected = {f"country_{good}_{direction}_tariffs_rate_add"
                    for good in ("coal", "oil") for direction in ("import", "export")}
        self.assertEqual(set(definitions), expected)
        self.assertEqual({key for key in modifier if "tariffs" in key}, expected)
        from test_gw_top_emitters import _loc
        for key in expected:
            self.assertEqual(modifier[key], "0.10")
            self.assertEqual(definitions[key]["percent"], "yes")
            self.assertNotIn("script_only", definitions[key])
            self.assertTrue(_loc(key))
            self.assertTrue(_loc(key + "_desc"))
        self.assertNotIn("country_greenhouse_gas_emissions_mult", modifier)
        self.assertEqual(modifier["country_authority_cost_add"], "100")

    def test_tariff_policy_does_not_write_native_levels_or_store_override_state(self):
        effects = load(EFFECTS)
        adopt = effects["gw_effect_fossil_fuel_tariffs"]["custom_tooltip"]
        repeal = effects["gw_effect_remove_fossil_fuel_tariffs"]["custom_tooltip"]
        self.assertEqual(adopt["je:je_global_warming"],
                         {"add_modifier": {"name": "fossil_fuel_tariffs_modifier"}})
        self.assertEqual(repeal["je:je_global_warming"],
                         {"remove_modifier": "fossil_fuel_tariffs_modifier"})
        for name, effect in effects.items():
            if "tariff" in name:
                for write in ("set_import_tariff_level", "set_export_tariff_level", "set_variable"):
                    self.assertNotIn(write, str(effect), name)

    def test_market_leader_controls_rates_while_legislated_customs_can_coexist(self):
        triggers = load(TRIGGERS)
        for name in ("gw_possible_fossil_fuel_tariffs", "gw_possible_remove_fossil_fuel_tariffs"):
            self.assertIn("te_tax_owns_market", str(triggers[name]))
            self.assertNotIn("te_tax_customs_on", str(triggers[name]))
            self.assertNotIn("gw_bound_by_emissions_treaty", str(triggers[name]))
        active = triggers["gw_policy_fossil_fuel_tariffs_active"]
        self.assertEqual(active["market_capital"]["owner"]["je:je_global_warming"],
                         {"has_modifier": "fossil_fuel_tariffs_modifier"})

    def test_cleanup_removes_only_former_leaders_tariff_marker(self):
        effects = load(EFFECTS)
        cleanup = effects["gw_refresh_fossil_fuel_tariffs_effect"]["if"]
        self.assertEqual(cleanup["limit"]["OR"], {"NOT": [
            {"te_tax_owns_market": "yes"}, {"has_game_rule": "global_warming_enabled"}]})
        self.assertEqual(cleanup["gw_drop_fossil_fuel_tariffs_effect"], "yes")
        self.assertEqual(effects["gw_drop_fossil_fuel_tariffs_effect"], {
            "je:je_global_warming": {"remove_modifier": "fossil_fuel_tariffs_modifier"}})
        pulse = load("common/on_actions/extra_on_actions.txt")["global_warming_events_on_action"]["effect"]
        self.assertEqual(pulse["gw_refresh_tariff_policies_effect"], "yes")


class RenewableInvestmentCostTest(unittest.TestCase):
    """Renewable Investment pays 0.5% of GDP a year, not forced plant subsidies (2026-10-20)."""

    COST = "renewable_investment_cost_modifier"

    def test_policy_modifier_keeps_its_bonuses_and_forces_no_subsidies(self):
        modifier = load("common/static_modifiers/extra_modifiers.txt")["renewable_investment_modifier"]
        self.assertNotIn("require_subsidies", str(modifier))
        self.assertEqual(modifier["building_renewable_energy_plant_throughput_add"], "0.20")
        self.assertEqual(modifier["building_power_plant_throughput_add"], "-0.10")
        # Construction speed targets the clean plants' own group, not all of bg_power.
        self.assertEqual(modifier["building_group_bg_clean_power_construction_efficiency_add"], "0.25")
        self.assertNotIn("building_group_bg_power_construction_efficiency_add", modifier)
        self.assertNotIn("country_expenses_add", modifier)
        # The retired bool has no definition and no loc left behind.
        self.assertNotIn("country_building_renewable_energy_plant_require_subsidies_bool",
                         load("common/modifier_type_definitions/global_warming_modifier_types.txt"))
        from test_gw_top_emitters import _loc
        with self.assertRaises(AssertionError):
            _loc("country_building_renewable_energy_plant_require_subsidies_bool")

    def test_clean_plants_sit_in_a_child_group_of_bg_power_and_the_coal_plant_does_not(self):
        groups = load("common/building_groups/extra_building_groups.txt")
        group = groups["REPLACE_OR_CREATE:bg_clean_power"]
        self.assertEqual(group["parent_group"], "bg_power")
        # Needed for building_group_bg_clean_power_construction_efficiency_add to exist.
        self.assertEqual(group["construction_efficiency_modifier"], "yes")
        # Restated at bg_power's vanilla values, as every vanilla child group restates them.
        bg_power = json.loads((ROOT / "vanilla_parsed/common/building_groups.json").read_text(encoding="utf-8"))["bg_power"][1]
        for key in ("lens", "urbanization", "economy_of_scale_ai_factor", "infrastructure_usage_per_level"):
            self.assertEqual(group[key], bg_power[key][1], key)
        buildings = load("common/buildings/extra_buildings.txt")
        for name in ("hydro_plant", "nuclear_plant", "fusion_plant", "renewable_energy_plant"):
            self.assertEqual(buildings[f"REPLACE_OR_CREATE:building_{name}"]["building_group"], "bg_clean_power", name)
        # The mod leaves the coal and oil plant (and every other building) out of the child group,
        # and puts nothing in bg_power itself that the group should hold.
        self.assertEqual([name for name, block in buildings.items() if isinstance(block, dict)
                          and block.get("building_group") == "bg_power"], [])
        modifier_type = load("common/modifier_type_definitions/mod_entity_modifier_types.txt")
        self.assertIn("building_group_bg_clean_power_construction_efficiency_add", modifier_type)
        from test_gw_top_emitters import _loc
        for key in ("bg_clean_power", "building_group_bg_clean_power_construction_efficiency_add",
                    "building_group_bg_clean_power_construction_efficiency_add_desc"):
            self.assertTrue(_loc(key), key)

    def test_cost_is_a_gdp_scaled_expense_mirrored_into_the_budget_breakdown(self):
        modifier = load("common/static_modifiers/extra_modifiers.txt")[self.COST]
        self.assertEqual(modifier["country_expenses_add"], "1")
        self.assertEqual(modifier["country_te_budget_expense_climate_add"], "1")
        # 0.5% of a year's GDP, paid weekly.
        self.assertEqual(load("common/script_values/global_warming_cost_values.txt")["gw_renewable_investment_cost_value"],
                         {"value": "gdp", "multiply": "0.005", "divide": "52", "min": "0"})
        from test_gw_top_emitters import _loc
        for key in (self.COST, self.COST + "_desc", "renewable_investment_modifier_desc"):
            self.assertTrue(_loc(key), key)

    def test_cost_goes_on_and_off_with_the_policy(self):
        effects = load(EFFECTS)
        adopt = effects["gw_effect_renewable_investment"]
        repeal = effects["gw_effect_remove_renewable_investment"]["custom_tooltip"]
        # Outside the adopt custom_tooltip, so the tooltip prints the cost (GW-4).
        self.assertEqual(adopt["gw_renewable_investment_cost_apply"], "yes")
        self.assertNotIn("gw_renewable_investment_cost_apply", adopt["custom_tooltip"])
        self.assertEqual(repeal["remove_modifier"], self.COST)
        # The removal comes first: after the add it would strip the fresh cost.
        self.assertEqual(effects["gw_renewable_investment_cost_apply"], {
            "remove_modifier_if_exists_effect": {"MODIFIER": self.COST},
            "add_modifier": {"name": self.COST, "multiplier": "gw_renewable_investment_cost_value"}})
        self.assertEqual(list(effects["gw_renewable_investment_cost_apply"]),
                         ["remove_modifier_if_exists_effect", "add_modifier"])
        treaty = load("common/treaty_articles/109_enforce_emissions_reduction.txt")["enforce_emissions_reduction"]
        self.assertIn("gw_renewable_investment_cost_apply", str(treaty["on_entry_into_force"]))

    def apply_cost(self, held):
        """Run gw_renewable_investment_cost_apply once on a scope holding the modifier names in `held`.

        The engine as the repo documents it: a same-name add_modifier stacks (it adds another copy), and
        has_modifier reads the scope as it was before the effect, because adds and removes land after it
        ends. A removal takes every copy of the name. Returns the scope's modifiers afterwards.
        """
        before = list(held)
        queued = []
        helper = load("common/scripted_effects/extra_effects.txt")["remove_modifier_if_exists_effect"]

        def run(body, args):
            for key, arg in body.items():
                if key == "add_modifier":
                    queued.append(("add", arg["name"]))
                elif key == "remove_modifier":
                    queued.append(("remove", args.get(arg, arg)))
                elif key == "remove_modifier_if_exists_effect":
                    run(helper, {"$MODIFIER$": arg["MODIFIER"]})
                elif key == "if":
                    if args.get(arg["limit"]["has_modifier"], arg["limit"]["has_modifier"]) in before:
                        run({k: v for k, v in arg.items() if k != "limit"}, args)
                else:
                    self.fail(f"gw_renewable_investment_cost_apply uses {key}, which this model cannot run")

        run(load(EFFECTS)["gw_renewable_investment_cost_apply"], {})
        after = list(held)
        for op, name in queued:
            after = [m for m in after if m != name] if op == "remove" else after + [name]
        return after

    def test_reapplying_the_cost_replaces_it_instead_of_stacking(self):
        """The monthly sweep re-applies the cost for every adopter; a pass must not add a second copy.

        Before the fix the apply effect was a bare add_modifier, so each month stacked another
        full-size weekly cost (2026-10-20).
        """
        held = []
        for month in range(1, 13):
            held = self.apply_cost(held)
            self.assertEqual(held, [self.COST], f"after {month} monthly passes")

    def test_monthly_sweep_follows_the_policy_with_the_climate_rule_on_or_off(self):
        effects = load(EFFECTS)
        sync = effects["gw_renewable_investment_cost_sync"]
        self.assertEqual(sync["if"]["limit"], {"gw_policy_renewable_investment_active": "yes"})
        self.assertEqual(sync["if"]["gw_renewable_investment_cost_apply"], "yes")
        self.assertEqual(sync["else_if"]["remove_modifier"], self.COST)
        sweep = effects["gw_refresh_policy_costs_effect"]["every_country"]
        self.assertEqual(sweep["gw_renewable_investment_cost_sync"], "yes")
        self.assertEqual(sweep["limit"]["OR"], {"has_journal_entry": "je_global_warming", "has_modifier": self.COST})
        pulse = load("common/on_actions/extra_on_actions.txt")["global_warming_events_on_action"]["effect"]
        self.assertEqual(pulse["gw_refresh_policy_costs_effect"], "yes")


if __name__ == "__main__":
    unittest.main()
