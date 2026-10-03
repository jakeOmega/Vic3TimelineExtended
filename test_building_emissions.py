"""Phase-1 recipe/accounting checks; engine behavior needs the opt-in probe."""

import copy
import json
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import gen_carbon_capture_pms as gen
from paradox_file_parser import ParadoxFileParser
from vanilla_parsed import decode

ROOT = Path(__file__).resolve().parent


def parsed(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(ROOT / path), apply_directives=False)
    return parser.data


def body(data, key):
    return gen.unwrap(data[key])


def workforce(method):
    return body(body(gen.unwrap(method), "building_modifiers"), "workforce_scaled")


def scalar(data, key):
    return Decimal(body(data, key))


class SyntheticCreditsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.methods = gen.load_synthetic_methods(ROOT)
        cls.generated = parsed(gen.OUTPUT)
        cls.factors = parsed("common/script_values/greenhouse_gas_factors.txt")

    def test_fuel_weights_and_display_scale(self):
        self.assertEqual(scalar(self.factors, "gw_emission_factor_coal"), 2)
        self.assertEqual(scalar(self.factors, "gw_emission_factor_oil"), Decimal("1.74"))
        self.assertEqual(scalar(self.factors, "gw_emission_display_scale"), 1000)

    def test_generated_credits_match_each_recipe_and_factor(self):
        expected = {
            "pm_synthetic_oil_1": Decimal("-0.03132"),
            "pm_synthetic_oil_2": Decimal("-0.05220"),
            "pm_synthetic_coal": Decimal("-0.16800"),
        }
        for pm, fuel in gen.SYNTHETIC_METHODS.items():
            with self.subTest(pm=pm):
                credit = body(self.generated, f"gw_{pm[3:]}_capture_per_level")
                factor_name = body(credit, "multiply")
                self.assertEqual(factor_name, f"gw_emission_factor_{fuel}")
                recipe_output = scalar(workforce(self.methods[pm]), f"goods_output_{fuel}_add")
                self.assertEqual(scalar(credit, "value"), -recipe_output)
                self.assertEqual(
                    scalar(credit, "value") * scalar(self.factors, factor_name)
                    / scalar(credit, "divide"), expected[pm],
                )

    def test_recipe_change_updates_credit_without_changing_generator(self):
        methods = copy.deepcopy(self.methods)
        workforce(methods["pm_synthetic_oil_2"])["goods_output_oil_add"] = ("=", "400")
        output = gen.build_synthetic_values(methods)
        self.assertIn("value = -400", output)
        self.assertNotIn("value = -300", output)

    def test_invalid_output_fails_before_writing(self):
        for amount in ("0", "-10", "NaN", "Infinity"):
            methods = copy.deepcopy(self.methods)
            workforce(methods["pm_synthetic_oil_2"])["goods_output_oil_add"] = ("=", amount)
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                gen.build_synthetic_values(methods)

    def test_missing_recipe_fails(self):
        with self.assertRaises(KeyError):
            gen.build_synthetic_values({})

    def test_post_load_entrypoint_and_idempotent_write(self):
        # Exercise the actual ModState entity key, not only the standalone CLI.
        ms = SimpleNamespace(mod_parsers={"PMs": SimpleNamespace(data=self.methods)})
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(gen.regenerate(ms, root=root, dry_run=True)["changed"])
            self.assertFalse((root / gen.OUTPUT).exists())
            self.assertTrue(gen.regenerate(ms, root=root)["changed"])
            target = root / gen.OUTPUT
            stamp = target.stat().st_mtime_ns
            self.assertFalse(gen.regenerate(ms, root=root)["changed"])
            self.assertEqual(target.stat().st_mtime_ns, stamp)
            self.assertEqual(target.read_bytes(), gen.build_synthetic_values(self.methods).encode("utf-8-sig"))

    def test_committed_output_is_current(self):
        self.assertFalse(gen.regenerate(root=ROOT, dry_run=True)["changed"])


class SteelRecipeTest(unittest.TestCase):
    def test_vanilla_arc_injection_preserves_unrelated_fields_and_goods_cost(self):
        vanilla = decode(json.loads((ROOT / "vanilla_parsed/common/pms.json").read_text()))
        before = copy.deepcopy(vanilla["pm_electric_arc_process"])
        parser = ParadoxFileParser()
        parser.data = {"pm_electric_arc_process": copy.deepcopy(before)}
        parser.parse_file(str(ROOT / "common/production_methods/steel_emissions_inputs.txt"))
        after = parser.data["pm_electric_arc_process"]
        inputs = workforce(after)
        self.assertEqual(scalar(inputs, "goods_input_coal_add"), 10)
        self.assertEqual(scalar(inputs, "goods_input_electricity_add"), 50)
        self.assertEqual(
            scalar(inputs, "goods_input_coal_add") + scalar(inputs, "goods_input_electricity_add"),
            scalar(workforce(before), "goods_input_coal_add")
            + scalar(workforce(before), "goods_input_electricity_add"),
        )
        # Remove the two changed keys, then compare the complete recipes.
        for recipe in (before, after):
            for key in ("goods_input_coal_add", "goods_input_electricity_add"):
                workforce(recipe).pop(key)
        self.assertEqual(before, after)

    def test_substitutions_reduce_coal_without_changing_total_input_value(self):
        pms = parsed("common/production_methods/extra_pms.txt")
        for name, original_cost in (("pm_aluminum_substitution", 9400), ("pm_chromium_substitution", 11400)):
            inputs = workforce(pms[name])
            with self.subTest(name=name):
                self.assertEqual(scalar(inputs, "goods_input_coal_add"), 10)
                self.assertEqual(scalar(inputs, "goods_input_electricity_add"), 170)
                total = scalar(inputs, "goods_input_iron_add") * 40
                total += scalar(inputs, "goods_input_coal_add") * 30
                total += scalar(inputs, "goods_input_electricity_add") * 30
                self.assertEqual(total, original_cost)


class DisplayBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = parsed("common/script_values/global_warming_values.txt")
        cls.extra = parsed("common/script_values/extra_script_values.txt")

    def test_formatted_amounts_scale_only_at_read_boundary(self):
        for name, raw in (("gw_market_emis_display", "gw_market_emis_raw"),
                          ("gw_global_emis_display", "gw_global_emis_raw")):
            value = body(self.values, name)
            self.assertEqual(body(value, "value"), raw)
            self.assertEqual(body(value, "multiply"), "gw_emission_display_scale")
        for name in ("gw_disp_own_emis", "gw_disp_own_cum", "gw_disp_captured"):
            multiplies = body(self.values, name)["multiply"]
            self.assertIn(("=", "gw_emission_display_scale"), multiplies if isinstance(multiplies, list) else [multiplies])
        display = body(self.extra, "market_greenhouse_gas_emissions_script_value_display")
        self.assertEqual(body(display, "multiply"), "gw_emission_display_scale")

    def test_share_and_temperature_use_internal_units(self):
        share = body(body(self.values, "gw_share_pct_display"), "if")
        self.assertEqual(body(share, "add"), "gw_market_emis_raw")
        self.assertEqual(body(share, "divide"), "global_var:gw_g_global_emis")
        yearly = body(self.values, "gw_yearly_change_display")
        self.assertEqual(body(yearly, "value"), "gw_global_emis_raw")
        self.assertEqual(scalar(yearly, "divide"), 10000)
        # The live world sum is also the debug helper's internal snapshot input.
        live = (ROOT / "common/script_values/extra_script_values.txt").read_text(encoding="utf-8-sig")
        live = live.split("global_greenhouse_gas_emissions_script_value_display = {", 1)[1].split("temperature_anomaly_display = {", 1)[0]
        self.assertNotIn("gw_emission_display_scale", live)

    def test_synthetic_sweep_uses_generated_values_and_staffing(self):
        text = (ROOT / "common/script_values/extra_script_values.txt").read_text(encoding="utf-8-sig")
        capture = text.split("market_carbon_capture_script_value = {", 1)[1].split("market_greenhouse_gas_emissions_script_value_display = {", 1)[0]
        for pm in gen.SYNTHETIC_METHODS:
            self.assertIn(f"multiply = gw_{pm[3:]}_capture_per_level", capture)
        self.assertEqual(capture.count("multiply = occupancy"), 3)
        for old in ("multiply = -0.06", "multiply = -0.036", "multiply = -0.168"):
            self.assertNotIn(old, capture)

    def test_market_consumption_uses_shared_weights_without_rescaling(self):
        value = body(self.extra, "market_greenhouse_gas_emissions_script_value")
        market = body(value, "market")
        for fuel in ("coal", "oil"):
            contribution = body(body(market, f"mg:{fuel}"), "add")
            self.assertEqual(body(contribution, "value"), "market_goods_consumption")
            self.assertEqual(body(contribution, "multiply"), f"gw_emission_factor_{fuel}")
        self.assertEqual(scalar(value, "divide"), 10000)
        self.assertEqual(body(value, "multiply"), "gw_emission_multiplier_script_value")


if __name__ == "__main__":
    unittest.main()
