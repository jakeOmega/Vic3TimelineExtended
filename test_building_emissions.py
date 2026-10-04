"""Phase-1 recipe/accounting checks; engine behavior needs the opt-in probe."""

import copy
import json
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest import mock

import gen_carbon_capture_pms as gen
import pm_emissions as emissions
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


def state_scaled(method):
    """The method's workforce-scaled state modifiers, or {} when it has none."""
    state = gen.unwrap(gen.unwrap(method).get("state_modifiers", {}))
    return gen.unwrap(state.get("workforce_scaled", {})) if isinstance(state, dict) else {}


def scalar(data, key):
    return Decimal(body(data, key))


class SyntheticCreditsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = emissions.load_state(ROOT)
        cls.methods = {name: cls.state.mod_parsers["PMs"].data[name] for name in emissions.SYNTHETIC_CREDITS}
        cls.factors = parsed("common/script_values/greenhouse_gas_factors.txt")

    def test_fuel_weights_and_display_scale(self):
        self.assertEqual(scalar(self.factors, "gw_emission_factor_coal"), 2)
        self.assertEqual(scalar(self.factors, "gw_emission_factor_oil"), Decimal("1.74"))
        self.assertEqual(scalar(self.factors, "gw_emission_display_scale"), 1000)

    def test_recipe_change_updates_net_and_credit_without_changing_generator(self):
        state = copy.copy(self.state)
        state.mod_parsers = dict(self.state.mod_parsers)
        state.mod_parsers["PMs"] = copy.copy(self.state.mod_parsers["PMs"])
        state.mod_parsers["PMs"].data = copy.deepcopy(self.state.mod_parsers["PMs"].data)
        workforce(state.mod_parsers["PMs"].data["pm_synthetic_oil_2"])["goods_output_oil_add"] = ("=", "400")
        output = emissions.plan_outputs(state, ROOT)[0][Path("common/production_methods/extra_pms.txt")]
        self.assertNotIn("state_carbon_capture_add", output)
        self.assertIn("state_greenhouse_gas_emissions_add = -69.60", output)
        for amount in ("0", "-10", "NaN", "Infinity"):
            workforce(state.mod_parsers["PMs"].data["pm_synthetic_oil_2"])["goods_output_oil_add"] = ("=", amount)
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                emissions.plan_outputs(state, ROOT)

    def test_post_load_entrypoint_and_idempotent_write(self):
        # Exercise the actual ModState entity key, not only the standalone CLI.
        ms = SimpleNamespace(
            mod_parsers={"PMs": SimpleNamespace(data={
                             **self.methods,
                             **{name: self.state.mod_parsers["PMs"].data[name] for name in emissions.NETTED_FUEL},
                             "pm_direct_air_capture": parsed("common/production_methods/direct_air_capture.txt")["pm_direct_air_capture"]}),
                         "PM Groups": SimpleNamespace(data={}),
                         "Buildings": SimpleNamespace(data={
                             name: {"production_method_groups": ("=", [])}
                             for name in ("building_power_plant", "building_steel_mill", "building_chemical_plant")})},
            base_parsers={"PMs": SimpleNamespace(data={})},
        )
        fixture = emissions.load_state(ROOT)
        for kind in ("Buy Packages", "Goods", "Pop Needs", "Pop Types"):
            ms.mod_parsers[kind] = fixture.mod_parsers[kind]
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / emissions.FACTORS).parent.mkdir(parents=True)
            (root / emissions.FACTORS).write_bytes((ROOT / emissions.FACTORS).read_bytes())
            removal_path = Path("common/production_methods/direct_air_capture.txt")
            (root / removal_path).parent.mkdir(parents=True, exist_ok=True)
            (root / removal_path).write_bytes((ROOT / removal_path).read_bytes())
            extra = Path("common/production_methods/extra_pms.txt")
            (root / extra).write_bytes((ROOT / extra).read_bytes())
            self.assertTrue(gen.regenerate(ms, root=root, dry_run=True)["changed"])
            self.assertFalse((root / emissions.OUTPUT).exists())
            self.assertTrue(gen.regenerate(ms, root=root)["changed"])
            target = root / emissions.OUTPUT
            stamp = target.stat().st_mtime_ns
            self.assertFalse(gen.regenerate(ms, root=root)["changed"])
            self.assertEqual(target.stat().st_mtime_ns, stamp)
            self.assertEqual(target.read_bytes(), emissions.plan_outputs(ms, root)[0][emissions.OUTPUT].encode("utf-8-sig"))

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


class BuildingEmissionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = emissions.load_state(ROOT)

    def test_covered_fuel_methods_use_merged_inputs(self):
        outputs, count = emissions.plan_outputs(self.state, ROOT)
        self.assertEqual(count, 248)
        self.assertEqual(set(outputs), {emissions.OUTPUT})
        pms = self.state.mod_parsers["PMs"].data
        for name, expected in (("pm_modern_coal-fired_plant", "5.00"),
                               ("pm_modern_oil-fired_plant", "6.09"),
                               ("pm_electric_arc_process", "2.00"),
                               ("pm_rotary_valve_engine_building_steel_mill", "2.00"),
                               ("pm_flow_chemistry_production", "38.28")):
            with self.subTest(name=name):
                self.assertEqual(scalar(state_scaled(pms[name]), emissions.STATE_MODIFIER), Decimal(expected))
        self.assertNotIn(emissions.STATE_MODIFIER, state_scaled(pms["pm_molecular_foundry"]))

    def test_no_method_carries_a_retired_emissions_field(self):
        # A method tooltip lists building and state modifiers alike, so the old
        # building-scoped copy of the state line showed every figure twice.
        for path in (ROOT / "common/production_methods").rglob("*.txt"):
            text = path.read_text(encoding="utf-8-sig")
            for retired in emissions.OBSOLETE_MODIFIERS:
                with self.subTest(path=path.name, retired=retired):
                    self.assertNotIn(retired, text)

    def test_coal_mine_counts_the_coal_vanilla_nets_out_of_its_output(self):
        pms = self.state.mod_parsers["PMs"].data
        stale = "vanilla changed the Coal Mine or Iron Mine pump recipes; re-derive NETTED_FUEL (pm_emissions.py)"
        for coal_pm, iron_pm in (("pm_atmospheric_engine_pump_building_coal_mine", "pm_atmospheric_engine_pump_building_iron_mine"),
                                 ("pm_condensing_engine_pump_building_coal_mine", "pm_condensing_engine_pump_building_iron_mine")):
            with self.subTest(method=coal_pm):
                coal, iron = workforce(pms[coal_pm]), workforce(pms[iron_pm])
                # The Coal Mine lists no coal input, so the recipe alone shows no fuel...
                self.assertNotIn("goods_input_coal_add", coal)
                # ...but its output is the iron mine's, scaled up and net of the iron mine's coal.
                burn = scalar(iron, "goods_input_coal_add")
                self.assertEqual(emissions.NETTED_FUEL[coal_pm], {"coal": burn}, stale)
                self.assertEqual(scalar(coal, "goods_output_coal_add"),
                                 Decimal("1.25") * scalar(iron, "goods_output_iron_add") - burn, stale)
                # Same machinery, same burn, so the two mines show the same emissions.
                self.assertEqual(scalar(state_scaled(pms[coal_pm]), emissions.STATE_MODIFIER),
                                 scalar(state_scaled(pms[iron_pm]), emissions.STATE_MODIFIER))
        donkey = workforce(pms["pm_steam_donkey_building_coal_mine"])
        self.assertNotIn("goods_input_coal_add", donkey)
        self.assertEqual(emissions.NETTED_FUEL["pm_steam_donkey_building_coal_mine"],
                         {"coal": -scalar(donkey, "goods_output_coal_add")}, stale)
        self.assertEqual(scalar(state_scaled(pms["pm_steam_donkey_building_coal_mine"]), emissions.STATE_MODIFIER),
                         Decimal("0.60"))

    def test_netted_fuel_rejects_a_double_count_and_unknown_methods(self):
        state = copy.copy(self.state)
        state.mod_parsers = dict(self.state.mod_parsers)
        state.mod_parsers["PMs"] = copy.copy(self.state.mod_parsers["PMs"])
        state.mod_parsers["PMs"].data = copy.deepcopy(self.state.mod_parsers["PMs"].data)
        pump = state.mod_parsers["PMs"].data["pm_atmospheric_engine_pump_building_coal_mine"]
        workforce(pump)["goods_input_coal_add"] = ("=", "10")
        with self.assertRaisesRegex(ValueError, "lists a coal input"):
            emissions.plan_outputs(state, ROOT)
        with mock.patch.dict(emissions.NETTED_FUEL, {"pm_no_such_method": {"coal": Decimal(1)}}):
            with self.assertRaisesRegex(ValueError, "not defined"):
                emissions.plan_outputs(self.state, ROOT)

    def test_every_reachable_fuel_recipe_has_a_visible_contribution(self):
        methods = self.state.mod_parsers["PMs"].data
        groups = self.state.mod_parsers["PM Groups"].data
        for building in self.state.mod_parsers["Buildings"].data.values():
            for group in body(gen.unwrap(building), "production_method_groups"):
                for name in body(gen.unwrap(groups[group]), "production_methods"):
                    amount = emissions.recipe_emissions(methods[name], {"coal": Decimal(2), "oil": Decimal("1.74")},
                                                        netted=emissions.netted_fuel(name, methods[name]))
                    if amount and name not in emissions.REMOVALS and name not in emissions.SYNTHETIC_CREDITS:
                        with self.subTest(method=name):
                            self.assertEqual(scalar(state_scaled(methods[name]), emissions.STATE_MODIFIER), amount)

    def test_generated_injects_target_only_untouched_vanilla(self):
        injects = parsed(emissions.OUTPUT)
        self.assertGreater(len(injects), 7)
        for key in injects:
            self.assertTrue(key.startswith("INJECT:"))
            self.assertIn(key[7:], self.state.base_parsers["PMs"].data)
        self.assertNotIn("INJECT:pm_coal-fired_plant", injects)
        self.assertNotIn("INJECT:pm_modern_coal-fired_plant", injects)

    def test_probe_capture_subtracts_from_gross_in_the_same_building(self):
        # The historical probe predates the state line and keeps its building-scoped cut.
        probe = parsed("docs/testing/carbon_capture_probe/common/production_methods/te_cc_probe_pms.txt")
        pms = self.state.mod_parsers["PMs"].data
        for fuel, expected in (("coal", "2.50"), ("oil", "3.04")):
            gross = scalar(state_scaled(pms[f"pm_modern_{fuel}-fired_plant"]), emissions.STATE_MODIFIER)
            capture = scalar(workforce(probe[f"pm_te_cc_probe_{fuel}"]), "building_greenhouse_gas_emissions_add")
            self.assertLess(capture, 0)
            self.assertEqual(gross + capture, Decimal(expected))

    def test_in_place_update_preserves_recipe_and_drops_retired_display_copy(self):
        block = """REPLACE:pm_test = {
\ttexture = "brace{#}"
\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_coal_add = 25
\t\t\tgoods_output_electricity_add = 90
\t\t}
\t}
} """
        retired = block.replace("\t\t\tgoods_input_coal_add",
                                "\t\t\tbuilding_greenhouse_gas_emissions_add = -2.50 # AUTO-GENERATED: fuel emissions\n"
                                "\t\t\tgoods_input_coal_add")
        stripped = retired
        for obsolete in emissions.OBSOLETE_MODIFIERS:
            stripped = emissions._with_state_modifier(stripped, Decimal(0), modifier=obsolete)
        self.assertEqual(stripped, block)
        updated = emissions._with_state_modifier(block, Decimal("5.00"), modifier=emissions.STATE_MODIFIER)
        self.assertIn('texture = "brace{#}"', updated)
        self.assertIn("goods_input_coal_add = 25", updated)
        self.assertEqual(emissions._with_state_modifier(updated, Decimal("5.00"), modifier=emissions.STATE_MODIFIER),
                         updated)
        amended = emissions._with_state_modifier(updated, Decimal("6.00"), modifier=emissions.STATE_MODIFIER)
        self.assertIn(f"{emissions.STATE_MODIFIER} = 6.00", amended)
        negative = emissions._with_state_modifier(updated, Decimal("-2.50"), modifier=emissions.STATE_MODIFIER)
        self.assertIn(f"{emissions.STATE_MODIFIER} = -2.50", negative)
        self.assertNotIn(emissions.STATE_MODIFIER,
                         emissions._with_state_modifier(negative, Decimal(0), modifier=emissions.STATE_MODIFIER))

    def test_recipe_invalid_inputs_fail(self):
        factors = {"coal": Decimal(2), "oil": Decimal("1.74")}
        method = {"building_modifiers": {"workforce_scaled": {"goods_input_coal_add": "25"}}}
        self.assertEqual(emissions.recipe_emissions(method, factors, Decimal(2000)), 10)
        for amount in ("-1", "NaN", "Infinity"):
            method = {"building_modifiers": {"workforce_scaled": {"goods_input_coal_add": amount}}}
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                emissions.recipe_emissions(method, factors)

    def test_changed_recipe_updates_or_removes_owned_emissions(self):
        state = SimpleNamespace(
            mod_parsers=dict(self.state.mod_parsers),
            base_parsers=self.state.base_parsers,
        )
        state.mod_parsers["PMs"] = SimpleNamespace(data=copy.deepcopy(self.state.mod_parsers["PMs"].data))
        method = workforce(state.mod_parsers["PMs"].data["pm_modern_coal-fired_plant"])
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in [emissions.FACTORS, *[p.relative_to(ROOT) for p in (ROOT / "common/production_methods").glob("*.txt")]]:
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_bytes((ROOT / relative).read_bytes())
            method["goods_input_coal_add"] = ("=", "30")
            output, count = emissions.plan_outputs(state, root)
            self.assertEqual(count, 248)
            rewritten = output[Path("common/production_methods/extra_pms.txt")]
            parser = ParadoxFileParser()
            parsed_path = root / "result.txt"
            parsed_path.write_text(rewritten, encoding="utf-8-sig")
            parser.parse_file(str(parsed_path), apply_directives=False)
            self.assertEqual(scalar(state_scaled(parser.data["pm_modern_coal-fired_plant"]), emissions.STATE_MODIFIER), 6)
            method["goods_input_coal_add"] = ("=", "0")
            output, count = emissions.plan_outputs(state, root)
            self.assertEqual(count, 247)
            parser = ParadoxFileParser()
            parsed_path.write_text(output[Path("common/production_methods/extra_pms.txt")], encoding="utf-8-sig")
            parser.parse_file(str(parsed_path), apply_directives=False)
            self.assertNotIn(emissions.STATE_MODIFIER, state_scaled(parser.data["pm_modern_coal-fired_plant"]))

    def test_cost_annotations_preserve_generated_modifier(self):
        import pm_costs

        block = """pm_test = {
\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_coal_add = 25
\t\t\tgoods_output_electricity_add = 90
\t\t}
\t}
}
"""
        generated = emissions._with_state_modifier(block, Decimal("5.00"), modifier=emissions.STATE_MODIFIER)
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "pms.txt"
            path.write_text(generated, encoding="utf-8-sig")
            pm_costs.process_and_update_production_methods_grouped(
                str(path), {"coal": 30, "electricity": 30},
                lambda *_: (750, 2700), lambda *_: 0,
            )
            annotated = path.read_text(encoding="utf-8-sig")
            self.assertIn(f"{emissions.STATE_MODIFIER} = 5.00", annotated)
            self.assertEqual(emissions._with_state_modifier(annotated, Decimal("5.00"), modifier=emissions.STATE_MODIFIER),
                             annotated)

    def test_state_lines_are_the_only_emissions_display(self):
        # script_only means the engine never reads the field; the tooltip still lists it.
        types = parsed("common/modifier_type_definitions/global_warming_modifier_types.txt")
        for modifier, color in ((emissions.STATE_MODIFIER, "bad"), (emissions.ATMOSPHERIC_MODIFIER, "good")):
            with self.subTest(modifier=modifier):
                display = body(types, modifier)
                self.assertEqual(body(display, "color"), color)
                self.assertEqual(body(display, "percent"), "no")
                self.assertEqual(scalar(display, "decimals"), 2)
                self.assertEqual(body(display, "script_only"), "yes")
        loc = "\n".join(p.read_text(encoding="utf-8-sig") for p in (ROOT / "localization/english").glob("*.yml"))
        self.assertTrue(f' {emissions.STATE_MODIFIER}:0 "Greenhouse Gas Emissions"' in loc, "state line name")
        for retired in emissions.OBSOLETE_MODIFIERS:
            with self.subTest(retired=retired):
                self.assertNotIn(retired, types)
                self.assertFalse(f" {retired}:" in loc, f"{retired} is still localized")


class DirectAirCaptureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pm = parsed("common/production_methods/direct_air_capture.txt")["pm_direct_air_capture"]
        cls.state = emissions.load_state(ROOT)

    def test_building_unlock_and_default_precede_synthetic_coal(self):
        building = body(self.state.mod_parsers["Buildings"].data, "building_synthetics_plant_coal")
        self.assertEqual(body(building, "unlocking_technologies"), ["carbon_capture_and_storage"])
        group = body(self.state.mod_parsers["PM Groups"].data, "pmg_synthetic_coal")
        self.assertEqual(body(group, "production_methods"), ["pm_direct_air_capture", "pm_synthetic_coal"])
        coal = body(self.state.mod_parsers["PMs"].data, "pm_synthetic_coal")
        self.assertEqual(body(coal, "unlocking_technologies"), ["genetic_engineering"])
        technology = body(parsed("common/technology/technologies/carbon_capture.txt"), "carbon_capture_and_storage")
        self.assertEqual(body(technology, "era"), "era_10")
        self.assertEqual(body(technology, "unlocking_technologies"), ["clean_energy_technologies"])
        # A captured works must retain a valid default even if its new owner
        # lacks the building's technology.
        self.assertNotIn("unlocking_technologies", gen.unwrap(self.pm))

    def test_removal_only_recipe_has_costs_workers_and_no_goods_output(self):
        inputs = workforce(self.pm)
        self.assertFalse(any(key.startswith("goods_output_") for key in inputs))
        self.assertEqual(scalar(inputs, "goods_input_electricity_add"), 1200)
        for key in ("goods_input_engines_add", "goods_input_steel_add", "goods_input_fertilizer_add"):
            self.assertGreater(scalar(inputs, key), 0)
        jobs = body(body(gen.unwrap(self.pm), "building_modifiers"), "level_scaled")
        self.assertEqual(sum(Decimal(gen.unwrap(value)) for value in jobs.values()), 5500)
        self.assertEqual(scalar(state_scaled(self.pm), emissions.ATMOSPHERIC_MODIFIER), 42)
        self.assertNotIn(emissions.STATE_MODIFIER, state_scaled(self.pm))

    def test_market_reads_staffed_removal_once_without_double_scaling(self):
        value = body(parsed("common/script_values/extra_script_values.txt"), "market_carbon_capture_script_value")
        countries = body(body(value, "market"), "every_scope_country")
        credit = body(body(countries, "every_scope_state"), "subtract")
        self.assertEqual(body(credit, "value"), "modifier:state_atmospheric_carbon_capture_add")
        self.assertEqual(body(credit, "divide"), "gw_emission_display_scale")
        self.assertNotIn("multiply", credit)
        self.assertNotIn("every_scope_building", countries)
        state = body(body(gen.unwrap(self.pm), "state_modifiers"), "workforce_scaled")
        self.assertEqual(scalar(state, emissions.ATMOSPHERIC_MODIFIER), 42)

    def test_removal_capacity_changes_independently_of_coal_output(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in [emissions.FACTORS, *[p.relative_to(ROOT) for p in (ROOT / "common/production_methods").glob("*.txt")]]:
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_bytes((ROOT / relative).read_bytes())
            path = root / emissions.FACTORS
            path.write_text(path.read_text(encoding="utf-8-sig").replace(
                "gw_direct_air_capture_coal_equivalent = 210", "gw_direct_air_capture_coal_equivalent = 420"),
                encoding="utf-8-sig")
            outputs, count = emissions.plan_outputs(self.state, root)
            self.assertEqual(count, 248)
            text = outputs[Path("common/production_methods/direct_air_capture.txt")]
            self.assertIn(f"{emissions.ATMOSPHERIC_MODIFIER} = 84.00", text)
            self.assertNotIn("goods_output_coal_add", text)
            self.assertNotIn(Path("common/production_methods/extra_pms.txt"), outputs)

    def test_support_is_national_and_requires_technology_without_free_emissions_cut(self):
        triggers = parsed("common/scripted_triggers/global_warming_triggers.txt")
        possible = body(triggers, "gw_possible_carbon_removal")
        self.assertEqual(body(possible, "has_technology_researched"), "carbon_capture_and_storage")
        self.assertNotIn("market_capital.owner", possible)
        modifier = body(parsed("common/static_modifiers/extra_modifiers.txt"), "carbon_removal_modifier")
        self.assertEqual(body(modifier, "country_building_synthetics_plant_coal_require_subsidies_bool"), "yes")
        self.assertEqual(scalar(modifier, "building_synthetics_plant_coal_throughput_add"), Decimal("0.05"))
        self.assertEqual(scalar(modifier, "country_authority_cost_add"), 100)
        self.assertNotIn("country_greenhouse_gas_emissions_mult", modifier)

    def test_support_can_be_rebuilt_from_inherited_country_state_and_repealed(self):
        effects = parsed("common/scripted_effects/global_warming_effects.txt")
        adopt = body(body(effects, "gw_effect_carbon_removal"), "custom_tooltip")
        repeal = body(body(effects, "gw_effect_remove_carbon_removal"), "custom_tooltip")
        flag = body(body(body(adopt, "hidden_effect"), "set_variable"), "name")
        self.assertEqual(body(body(repeal, "hidden_effect"), "remove_variable"), flag)
        self.assertNotIn("every_country", adopt)
        restore = body(body(effects, "gw_restore_carbon_removal_policy_effect"), "if")
        self.assertEqual(body(body(restore, "limit"), "has_variable"), flag)
        self.assertEqual(body(body(body(restore, "je:je_global_warming"), "add_modifier"), "name"),
                         "carbon_removal_modifier")
        self.assertEqual(body(body(repeal, "je:je_global_warming"), "remove_modifier"),
                         "carbon_removal_modifier")
        je = body(parsed("common/journal_entries/je_global_warming.txt"), "je_global_warming")
        pulse = body(body(je, "on_monthly_pulse"), "effect")
        self.assertEqual(body(pulse, "gw_restore_carbon_removal_policy_effect"), "yes")
        debug = parsed("common/scripted_effects/te_debug_gw_effects.txt")
        self.assertEqual(body(body(debug, "te_debug_gw_adopt_all"), "gw_effect_carbon_removal"), "yes")
        self.assertEqual(body(body(debug, "te_debug_gw_repeal_all"), "gw_effect_remove_carbon_removal"), "yes")


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

    def test_all_capture_uses_one_staffed_state_sweep(self):
        countries = body(body(body(self.extra, "market_carbon_capture_script_value"), "market"), "every_scope_country")
        credit = body(body(countries, "every_scope_state"), "subtract")
        self.assertEqual(body(credit, "value"), "modifier:state_atmospheric_carbon_capture_add")
        self.assertNotIn("every_scope_building", countries)
        methods = {name: emissions.load_state(ROOT).mod_parsers["PMs"].data[name] for name in emissions.SYNTHETIC_CREDITS}
        factors = parsed("common/script_values/greenhouse_gas_factors.txt")
        for name, fuel in emissions.SYNTHETIC_CREDITS.items():
            pm = gen.unwrap(methods[name])
            state = body(body(pm, "state_modifiers"), "workforce_scaled")
            expected = scalar(workforce(pm), f"goods_output_{fuel}_add") * scalar(factors, f"gw_emission_factor_{fuel}") / 10
            self.assertNotIn("state_carbon_capture_add", state)
            gross = emissions.recipe_emissions(pm, {"coal": Decimal(2), "oil": Decimal("1.74")})
            self.assertEqual(scalar(state, emissions.STATE_MODIFIER), gross - expected)

    def test_map_and_treaty_display_use_snapshots_without_live_household_sweeps(self):
        mapping = parsed("common/script_values/te_map_mode_script_values.txt")
        self.assertEqual(body(body(mapping, "te_map_mode_correction_for_emissions"), "value"), "owner.gw_market_emis_raw")
        loc = (ROOT / "localization/english/te_concepts_l_english.yml").read_text(encoding="utf-8-sig")
        treaty = next(line for line in loc.splitlines() if line.startswith(" enforce_emissions_reduction_article_short_desc:"))
        self.assertIn("SOURCE_COUNTRY.MakeScope.ScriptValue('gw_market_emis_display')", treaty)
        self.assertNotIn("market_greenhouse_gas_emissions_script_value", treaty)

    def test_market_uses_generated_state_emissions_without_consumption_proxy(self):
        value = body(self.extra, "market_greenhouse_gas_emissions_script_value")
        country = body(body(value, "market"), "every_scope_country")
        self.assertEqual(body(body(country, "every_scope_state"), "add"), "gw_state_greenhouse_gas_emissions")
        self.assertNotIn("divide", value)
        self.assertNotIn("multiply", value)
        state = body(self.extra, "gw_state_greenhouse_gas_emissions")
        self.assertEqual(body(state, "value"), "modifier:state_greenhouse_gas_emissions_add")
        self.assertEqual(body(state, "divide"), "gw_emission_display_scale")
        self.assertEqual(body(state, "add"), "gw_state_household_greenhouse_gas_emissions")
        removal = body(state, "subtract")
        self.assertEqual(body(removal, "value"), "modifier:state_atmospheric_carbon_capture_add")


if __name__ == "__main__":
    unittest.main()
