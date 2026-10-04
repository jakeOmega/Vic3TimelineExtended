"""National accounting and tariff lifecycle regressions using production scripts."""
from decimal import Decimal
import unittest

from test_household_emissions import Values, state
from test_tax_code_rule import load

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


if __name__ == "__main__":
    unittest.main()
