"""Source-capture coverage, validity, costs and regeneration regressions."""

from decimal import Decimal
from pathlib import Path
import unittest

import gen_law_consistency as law_gen
import pm_carbon_capture as capture
import pm_emissions as emissions
from test_building_emissions import body, parsed, scalar, workforce

ROOT = Path(__file__).resolve().parent


class CaptureGeneratorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = emissions.load_state(ROOT)
        cls.methods = cls.state.mod_parsers["PMs"].data
        cls.groups = cls.state.mod_parsers["PM Groups"].data
        cls.catalog, cls.attachments, cls.exceptions = capture.capture_catalog(cls.state)

    def test_all_fuel_consumers_are_captured_or_explicitly_exempt(self):
        exempt = {(b, g, m) for b, g, m, _ in self.exceptions}
        for building, value in self.state.mod_parsers["Buildings"].data.items():
            for group in body(emissions.unwrap(value), "production_method_groups"):
                if group.startswith(capture.PREFIX):
                    continue
                for pm in body(emissions.unwrap(self.groups[group]), "production_methods"):
                    if not any(capture.fuel_recipe(self.methods[pm])):
                        continue
                    with self.subTest(building=building, group=group, pm=pm):
                        if (building, group, pm) not in exempt:
                            self.assertIn(capture.PREFIX + group.removeprefix("pmg_"), self.attachments[building])
                            classes = self.catalog[group][0]
                            self.assertIn(pm, classes[capture.fuel_recipe(self.methods[pm])])

    def test_every_source_method_has_a_valid_mandated_choice(self):
        # A Tier-II-researched owner must have a valid choice for every source
        # PM, including zero-fuel/feedstock variants and alternative boilers.
        for source, (classes, exempt, _, _) in self.catalog.items():
            group = capture.PREFIX + source.removeprefix("pmg_")
            controls = body(emissions.unwrap(self.groups[group]), "production_methods")
            source_pms = body(emissions.unwrap(self.groups[source]), "production_methods")
            for pm in source_pms:
                valid = []
                for name in controls:
                    method = emissions.unwrap(self.methods[name])
                    if capture.MANDATE in emissions.unwrap(method.get("disallowing_laws", [])):
                        continue
                    gate = body(method, "unlocking_production_methods") if "unlocking_production_methods" in method else []
                    if not gate or pm in gate:
                        if "unlocking_technologies" not in method or body(method, "unlocking_technologies") == ["carbon_capture_and_storage"]:
                            valid.append(name)
                with self.subTest(group=group, pm=pm):
                    self.assertEqual(len(valid), 1)
                    self.assertIn("_na_" if pm in exempt else "_2_", valid[0])
            self.assertEqual(set(source_pms), set(exempt) | {p for names in classes.values() for p in names})

    def test_automation_and_process_controls_are_independent(self):
        self.assertEqual(len(self.attachments["building_steel_mill"]), 2)
        self.assertEqual(len(self.attachments["building_arms_industry"]), 2)
        self.assertEqual(self.attachments["building_arms_industry"][1], self.attachments["building_artillery_foundry"][1])

    def test_stationary_mine_pumps_but_not_mobile_excavators(self):
        source = "pmg_steam_automation_building_iron_mine"
        classes, exempt, _, _ = self.catalog[source]
        self.assertIn("pm_steam_donkey_mine", classes[(Decimal(4), Decimal(0))])
        self.assertIn("pm_dragline_excavators_iron_mine", exempt)

    def test_feedstock_transport_and_synthetic_fuel_exceptions(self):
        for building in ("building_port", "building_railway", "building_airport", "building_wheat_farm",
                         "building_synthetics_plant_oil", "building_synthetics_plant_rubber",
                         "building_synthetics_plant_silk", "building_standard_oil_refinery"):
            self.assertNotIn(building, self.attachments)
        self.assertIn("pm_houseware_plastics", self.catalog["pmg_base_building_glassworks"][1] if
                      "pmg_base_building_glassworks" in self.catalog else capture.EXCLUDED_METHODS)

    def test_capture_cuts_never_exceed_gross(self):
        generated = parsed(capture.METHODS)
        tiers = 0
        for name, value in generated.items():
            method = emissions.unwrap(value)
            if "state_modifiers" not in method:
                continue
            tiers += 1
            mirror = body(body(method, "state_modifiers"), "workforce_scaled")
            self.assertNotIn("state_carbon_capture_add", mirror)
            credit = -scalar(mirror, emissions.STATE_MODIFIER)
            self.assertGreater(credit, 0)
            self.assertNotIn("building_greenhouse_gas_emissions_add", workforce(method))
            self.assertNotIn("goods_input_coal_add", workforce(method))
            self.assertNotIn("goods_input_oil_add", workforce(method))
            for pm in body(method, "unlocking_production_methods"):
                gross = emissions.recipe_emissions(self.methods[pm], {"coal": Decimal(2), "oil": Decimal("1.74")})
                self.assertLessEqual(credit, gross)
                energy_loss = Decimal(body(workforce(method), "goods_output_electricity_add")) if "goods_output_electricity_add" in workforce(method) else 0
                if energy_loss:
                    self.assertGreater(Decimal(body(capture.workforce(self.methods[pm]), "goods_output_electricity_add")) + energy_loss, 0)
            self.assertTrue(any(k.startswith("goods_input_") for k in workforce(method)))
        self.assertEqual(tiers, 342)

    def test_modern_coal_tier_two_costs_follow_design_anchors(self):
        pm = self.methods["pm_carbon_capture_2_base_building_power_plant_coal25_oil0"]
        mirror = body(body(emissions.unwrap(pm), "state_modifiers"), "workforce_scaled")
        self.assertEqual(scalar(mirror, emissions.STATE_MODIFIER), Decimal("-2.50"))
        expected = {"goods_output_electricity_add": "-12",
                    "goods_input_engines_add": "5", "goods_input_steel_add": "6", "goods_input_fertilizer_add": "7"}
        for key, value in expected.items():
            self.assertEqual(scalar(workforce(pm), key), Decimal(value))

    def test_tiny_emitters_pay_costs_and_keep_fractional_capture(self):
        costs = capture.operating_costs((Decimal(0), Decimal("0.1")), Decimal("0.25"))
        self.assertGreater(costs["goods_input_electricity_add"], 0)
        self.assertGreater(costs["goods_input_engines_add"], 0)

    def test_building_injects_only_target_vanilla_and_owned_buildings_are_amended(self):
        injects = parsed(capture.BUILDINGS)
        for key in injects:
            self.assertTrue(key.startswith("INJECT:"))
            self.assertIn(key.removeprefix("INJECT:"), self.state.base_parsers["Buildings"].data)
        self.assertNotIn("INJECT:building_aerospace_industry", injects)
        self.assertNotIn("INJECT:building_generic_foundry_complex", injects)
        for building, added in self.attachments.items():
            actual = body(emissions.unwrap(self.state.mod_parsers["Buildings"].data[building]), "production_method_groups")
            self.assertEqual(len(actual), len(set(actual)))
            self.assertTrue(set(added) <= set(actual))

    def test_generation_is_current_and_preserves_building_fields(self):
        output, _ = capture.plan_outputs(self.state, ROOT)
        for relative, text in output.items():
            self.assertEqual((ROOT / relative).read_text(encoding="utf-8-sig"), text, relative)
        block = 'building_example = {\n\tproduction_method_groups = {\n\t\tpmg_original\n\t}\n\tpossible = { text = "brace{#}" }\n}\n'
        added = [capture.PREFIX + "example"]
        result = capture._with_groups(block, added)
        self.assertEqual(capture._with_groups(result, added), result)
        self.assertIn('possible = { text = "brace{#}" }', result)
        self.assertEqual(capture._with_groups(result, []), block)

    def test_market_credit_reads_state_once_in_location_market(self):
        market = body(body(parsed("common/script_values/extra_script_values.txt"), "market_carbon_capture_script_value"), "market")
        countries = body(market, "every_scope_country")
        state = body(countries, "every_scope_state")
        credit = body(state, "subtract")
        self.assertEqual(body(credit, "value"), "modifier:state_atmospheric_carbon_capture_add")
        self.assertEqual(body(credit, "divide"), "gw_emission_display_scale")
        self.assertNotIn("multiply", credit)

    def test_phaseout_technology_is_rechecked_for_held_law_only(self):
        law = {"unlocking_laws": [], "disallowing_laws": [], "unlocking_technologies": ["carbon_capture_and_storage"]}
        clause = law_gen._violation_clause(law, "", "law_managed_fossil_phaseout")
        self.assertIn("NOT = { has_technology_researched = carbon_capture_and_storage }", clause)
        self.assertEqual(law_gen._violation_clause(law, "", "law_other_legacy"), "")
        script = (ROOT / "common/scripted_effects/extra_law_consistency_generated.txt").read_text(encoding="utf-8-sig")
        helper = script.split("te_fix_inconsistent_lawgroup_resource_transition = {", 1)[1]
        self.assertIn("NOT = { has_technology_researched = carbon_capture_and_storage }", helper)


if __name__ == "__main__":
    unittest.main()
