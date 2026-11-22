"""National accounting and tariff lifecycle regressions using production scripts."""
from decimal import Decimal
import json
import re
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
        # The policy is the leader's variable, which je_global_warming's declaration follows (#1466).
        self.assertEqual(adopt["hidden_effect"],
                         {"set_variable": {"name": "gw_fossil_fuel_tariffs_policy", "value": "yes"}})
        self.assertEqual(repeal["hidden_effect"], {"remove_variable": "gw_fossil_fuel_tariffs_policy"})
        self.assertNotIn("je:je_global_warming", str(adopt) + str(repeal))
        for name, effect in effects.items():
            if "tariff" in name:
                for write in ("set_import_tariff_level", "set_export_tariff_level"):
                    self.assertNotIn(write, str(effect), name)
                # No saved levels or override state: the one variable is the policy itself.
                self.assertEqual(set(re.findall(r"'set_variable': \{'name': '(\w+)'", str(effect))) - {
                    "gw_fossil_fuel_tariffs_policy"}, set(), name)

    def test_market_leader_controls_rates_while_legislated_customs_can_coexist(self):
        triggers = load(TRIGGERS)
        for name in ("gw_possible_fossil_fuel_tariffs", "gw_possible_remove_fossil_fuel_tariffs"):
            self.assertIn("te_tax_owns_market", str(triggers[name]))
            self.assertNotIn("te_tax_customs_on", str(triggers[name]))
            self.assertNotIn("gw_bound_by_emissions_treaty", str(triggers[name]))
        active = triggers["gw_policy_fossil_fuel_tariffs_active"]
        self.assertEqual(active["market_capital"]["owner"], {"gw_runs_fossil_fuel_tariffs": "yes"})
        self.assertEqual(triggers["gw_runs_fossil_fuel_tariffs"],
                         {"has_journal_entry": "je_global_warming", "has_variable": "gw_fossil_fuel_tariffs_policy"})
        # The leader's own buttons read its own variable, not its market's.
        buttons = load("common/scripted_buttons/global_warming_buttons.txt")
        self.assertEqual(buttons["gw_fossil_fuel_tariffs_button"]["visible"]["NOT"], {"gw_runs_fossil_fuel_tariffs": "yes"})
        self.assertEqual(buttons["gw_remove_fossil_fuel_tariffs_button"]["visible"]["gw_runs_fossil_fuel_tariffs"], "yes")

    def test_cleanup_removes_only_former_leaders_tariff_marker(self):
        effects = load(EFFECTS)
        cleanup = effects["gw_refresh_fossil_fuel_tariffs_effect"]["if"]
        self.assertEqual(cleanup["limit"]["OR"], {"NOT": [
            {"te_tax_owns_market": "yes"}, {"has_game_rule": "global_warming_enabled"}]})
        self.assertEqual(cleanup["gw_drop_fossil_fuel_tariffs_effect"], "yes")
        self.assertEqual(cleanup["limit"]["gw_runs_fossil_fuel_tariffs"], "yes")
        self.assertEqual(effects["gw_drop_fossil_fuel_tariffs_effect"], {"if": {
            "limit": {"has_variable": "gw_fossil_fuel_tariffs_policy"},
            "remove_variable": "gw_fossil_fuel_tariffs_policy"}})
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
        buildings = {**load("common/buildings/extra_buildings.txt"), **load("common/buildings/06_zz_te_clean_power.txt")}
        for name in ("hydro_plant", "nuclear_plant", "fusion_plant", "renewable_energy_plant"):
            self.assertEqual(buildings[f"building_{name}"]["building_group"], "bg_clean_power", name)
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

    def declared(self):
        entry = load("common/journal_entries/je_global_warming.txt")["je_global_warming"]
        return {d["modifier"]: d["value"] for d in entry["scaling_modifiers_while_active"]}

    def test_cost_is_declared_on_the_entry_while_the_policy_is_in_force(self):
        """A scaling modifier on je_global_warming since #1404: the value's root is the country, so it reads
        gdp, and it follows the policy however that went on or off (the button, the widget, treaty 109, the
        debug console), with the climate rule on or off."""
        self.assertEqual(self.declared()[self.COST], {
            "value": "0",
            "if": {"limit": {"gw_policy_renewable_investment_active": "yes"},
                   "add": "gw_renewable_investment_cost_value"}})
        # The gate is the policy's variable (#1466), with no rule test.
        self.assertEqual(load(TRIGGERS)["gw_policy_renewable_investment_active"],
                         {"has_journal_entry": "je_global_warming", "has_variable": "gw_renewable_investment_policy"})

    def test_nothing_adds_or_re_applies_the_cost(self):
        effects = load(EFFECTS)
        for gone in ("gw_renewable_investment_cost_apply", "gw_renewable_investment_cost_sync",
                     "gw_refresh_policy_costs_effect"):
            self.assertNotIn(gone, effects)
        pulse = load("common/on_actions/extra_on_actions.txt")["global_warming_events_on_action"]["effect"]
        self.assertNotIn("gw_refresh_policy_costs_effect", pulse)
        repeal = effects["gw_effect_remove_renewable_investment"]["custom_tooltip"]
        self.assertEqual(repeal["hidden_effect"], {"remove_variable": "gw_renewable_investment_policy"})
        self.assertNotIn("remove_modifier", str(repeal))
        from test_gw_top_emitters import _loc
        self.assertIn("running cost", _loc("GW_REMOVE_RENEWABLE_INVESTMENT_DESC"))

    def test_adopting_previews_the_cost(self):
        """Outside the adopt custom_tooltip, so the tooltip prints the scaled Expenses line (GW-4); treaty 109,
        which forces the policy, calls the same adopt effect (#1466), so it previews it the same way."""
        preview = {"add_modifier": {"name": self.COST, "multiplier": "gw_renewable_investment_cost_value"}}
        adopt = load(EFFECTS)["gw_effect_renewable_investment"]
        self.assertEqual(adopt["show_as_tooltip"], preview)
        self.assertNotIn(self.COST, str(adopt["custom_tooltip"]))
        forced = TreatyForcedPoliciesTest.forced()
        self.assertEqual(forced["gw_policy_renewable_investment_active"], "gw_effect_renewable_investment")


class TreatyForcedPoliciesTest(unittest.TestCase):
    """Treaty 109 forces the source's seven policies through the adopt effects the panel calls, so each sets the
    policy's variable that je_global_warming's declaration follows and prints the policy (#1466)."""

    SEVEN = ("carbon_tax", "renewable_investment", "emission_standards", "reforestation", "public_transit",
             "fossil_fuel_divestment", "green_building_codes")

    @staticmethod
    def forced():
        """{in-force trigger: adopt effect} for each forced policy, inside the entry guard."""
        treaty = load("common/treaty_articles/109_enforce_emissions_reduction.txt")["enforce_emissions_reduction"]
        source = treaty["on_entry_into_force"]["scope:article_options"]["source_country"]
        guard = source["if"]
        assert guard["limit"] == {"has_journal_entry": "je_global_warming"}, guard["limit"]
        out = {}
        for block in guard["if"]:
            (trigger, _), = block["limit"]["NOT"].items()
            (effect, _), = ((k, v) for k, v in block.items() if k != "limit")
            out[trigger] = effect
        return out

    def test_each_forced_policy_goes_through_its_adopt_effect(self):
        self.assertEqual(self.forced(), {f"gw_policy_{p}_active": f"gw_effect_{p}" for p in self.SEVEN})
        text = (ROOT / "common/treaty_articles/109_enforce_emissions_reduction.txt").read_text(encoding="utf-8-sig")
        self.assertNotRegex(text, r"(add|remove|has)_modifier")

    def test_its_freeze_reads_the_same_seven(self):
        treaty = load("common/treaty_articles/109_enforce_emissions_reduction.txt")["enforce_emissions_reduction"]
        source = treaty["non_fulfillment"]["conditions"]["monthly"]["scope:article"]["source_country"]
        self.assertEqual(source["has_journal_entry"], "je_global_warming")
        self.assertEqual(source["OR"]["NOT"], [{f"gw_policy_{p}_active": "yes"} for p in (
            "carbon_tax", "renewable_investment", "emission_standards", "reforestation", "fossil_fuel_divestment",
            "green_building_codes", "public_transit")])


class PolicyDeclarationTest(unittest.TestCase):
    """The nine flat policies are scaling modifiers on je_global_warming at 1 while their country variable is set
    (#1466), as Carbon Removal Support and Aerosol Injection have been since #1404: a civil war's winner inherits
    the variables but no modifiers, so it keeps the policies, and nothing adds, removes or tests the modifiers
    (test_journal_entry_shape.py holds the tree to that)."""

    # modifier -> (variable, in-force trigger, adopt/repeal effect suffix)
    NINE = {
        "carbon_tax_modifier": ("gw_carbon_tax_policy", "gw_policy_carbon_tax_active", "carbon_tax"),
        "renewable_investment_modifier": ("gw_renewable_investment_policy", "gw_policy_renewable_investment_active",
                                          "renewable_investment"),
        "climate_adaptation_modifier": ("gw_climate_adaptation_policy", "gw_policy_climate_adaptation_active",
                                        "climate_adaptation"),
        "emission_standards_modifier": ("gw_emission_standards_policy", "gw_policy_emission_standards_active",
                                        "emission_standards"),
        "reforestation_subsidies_modifier": ("gw_reforestation_policy", "gw_policy_reforestation_active",
                                             "reforestation"),
        "public_transit_modifier": ("gw_public_transit_policy", "gw_policy_public_transit_active", "public_transit"),
        "fossil_fuel_divestment_modifier": ("gw_fossil_fuel_divestment_policy",
                                            "gw_policy_fossil_fuel_divestment_active", "fossil_fuel_divestment"),
        "green_building_codes_modifier": ("gw_green_building_codes_policy", "gw_policy_green_building_codes_active",
                                          "green_building_codes"),
        "fossil_fuel_tariffs_modifier": ("gw_fossil_fuel_tariffs_policy", "gw_runs_fossil_fuel_tariffs",
                                         "fossil_fuel_tariffs"),
    }

    def declared(self):
        entry = load("common/journal_entries/je_global_warming.txt")["je_global_warming"]
        return {d["modifier"]: d["value"] for d in entry["scaling_modifiers_while_active"]}

    def test_each_is_declared_at_one_while_its_variable_is_set(self):
        declared = self.declared()
        for modifier, (variable, _, _) in self.NINE.items():
            with self.subTest(modifier=modifier):
                self.assertEqual(declared[modifier],
                                 {"value": "0", "if": {"limit": {"has_variable": variable}, "add": "1"}})

    def test_in_force_reads_the_variable_while_the_entry_is_active(self):
        triggers = load(TRIGGERS)
        for _, (variable, trigger, _) in self.NINE.items():
            with self.subTest(trigger=trigger):
                self.assertEqual(triggers[trigger], {"has_journal_entry": "je_global_warming", "has_variable": variable})

    def test_adopt_sets_and_repeal_removes_the_variable_behind_the_policy_text(self):
        effects = load(EFFECTS)
        for modifier, (variable, _, suffix) in self.NINE.items():
            with self.subTest(policy=suffix):
                adopt = effects[f"gw_effect_{suffix}"]["custom_tooltip"]
                repeal = effects[f"gw_effect_remove_{suffix}"]["custom_tooltip"]
                # The text prints the policy; the hidden variable is the change.
                self.assertEqual(adopt["text"], f'"GW_{suffix.upper()}_DESC"')
                self.assertEqual(adopt["hidden_effect"], {"set_variable": {"name": variable, "value": "yes"}})
                self.assertEqual(repeal["text"], f'"GW_REMOVE_{suffix.upper()}_DESC"')
                self.assertEqual(repeal["hidden_effect"], {"remove_variable": variable})
                self.assertNotIn(modifier, str(adopt) + str(repeal))

    def test_the_ai_buttons_read_the_in_force_triggers(self):
        buttons = load("common/scripted_buttons/global_warming_buttons.txt")
        for _, (_, trigger, suffix) in self.NINE.items():
            with self.subTest(policy=suffix):
                self.assertEqual(buttons[f"gw_{suffix}_button"]["visible"]["NOT"], {trigger: "yes"})
                self.assertEqual(buttons[f"gw_remove_{suffix}_button"]["visible"][trigger], "yes")


if __name__ == "__main__":
    unittest.main()
