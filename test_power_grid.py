"""Power grids, phase 1: the Grid Transfer Station and Grid Power.

Static checks on the pieces the engine gives no warning for when they are
wrong: the station's method keeps its 1-unit lines of both goods (the flow
modifiers are _mult modifiers that scale them), each flow modifier scales the
right pair of lines, every Grid Power goods modifier is registered (a mod good
gets none from vanilla), base_values carries the one-per-state cap and the
mandatory subsidy, the modifiers are applied with local-variable multipliers
(a var: or script value there would resolve against the country), and the
monthly pulse is wired.

Run: python3 test_power_grid.py
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
COMMON = os.path.join(REPO, "common")
GOODS = os.path.join(COMMON, "goods", "timeline_extended_extra_goods.txt")
BUILDING = os.path.join(COMMON, "buildings", "power_grid.txt")
PMGS = os.path.join(COMMON, "production_method_groups", "power_grid_pmgs.txt")
PMS = os.path.join(COMMON, "production_methods", "power_grid_pms.txt")
MODIFIERS = os.path.join(COMMON, "static_modifiers", "power_grid_modifiers.txt")
EXTRA_MODIFIERS = os.path.join(COMMON, "static_modifiers", "extra_modifiers.txt")
TYPES = os.path.join(COMMON, "modifier_type_definitions", "mod_entity_modifier_types.txt")
EFFECTS = os.path.join(COMMON, "scripted_effects", "power_grid_effects.txt")
TRIGGERS = os.path.join(COMMON, "scripted_triggers", "power_grid_triggers.txt")
VALUES = os.path.join(COMMON, "script_values", "power_grid_values.txt")
ON_ACTIONS = os.path.join(COMMON, "on_actions", "power_grid_on_actions.txt")
TEXTICONS = os.path.join(REPO, "gui", "zzz_extra_goods_texticons.gui")
LOC_DIR = os.path.join(REPO, "localization", "english")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _block_from(text, start):
    depth = 1
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start:j]
    raise AssertionError("unbalanced braces")


def _top_level(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert m, f"no top-level {name}"
    return _block_from(text, m.end())


def _sub(block, key):
    m = re.search(rf"\b{re.escape(key)} = \{{", block)
    assert m, f"no {key} block"
    return _block_from(block, m.end())


def _code(text):
    """The text without comments."""
    return re.sub(r"#[^\n]*", "", text)


class GoodTest(unittest.TestCase):
    def test_grid_power_is_a_non_local_untradeable_good_at_electricitys_price(self):
        good = _code(_top_level(_read(GOODS), "grid_power"))
        self.assertRegex(good, r"\bcost = 30\b")
        self.assertRegex(good, r"\btradeable = no\b")
        self.assertNotRegex(good, r"\blocal = yes\b")

    def test_grid_power_has_a_texticon(self):
        self.assertRegex(_read(TEXTICONS), r"icon = grid_power\b")


class BuildingTest(unittest.TestCase):
    def setUp(self):
        self.building = _code(_top_level(_read(BUILDING), "building_grid_transfer_station"))

    def test_private_infrastructure_one_per_state(self):
        self.assertRegex(self.building, r"building_group = bg_private_infrastructure\b")
        self.assertRegex(self.building, r"has_max_level = yes")
        self.assertRegex(self.building, r"ignore_stateregion_max_level = yes")

    def test_method_groups(self):
        groups = _sub(self.building, "production_method_groups").split()
        self.assertEqual(groups, ["pmg_grid_transfer_station", "pmg_maintenance_heavy"])
        self.assertIn("pm_grid_transfer_base", _sub(_read(PMGS), "production_methods"))

    def test_possible_allows_the_own_state_a_neighbour_and_a_first_station(self):
        possible = _sub(self.building, "possible")
        self.assertIn("has_building = building_grid_transfer_station", possible)
        self.assertIn("any_neighbouring_state", possible)
        self.assertIn("is_in_same_market_area = ROOT", possible)


class MethodTest(unittest.TestCase):
    def test_base_method_carries_one_unit_of_each_line(self):
        scaled = _sub(_top_level(_read(PMS), "pm_grid_transfer_base"), "workforce_scaled")
        for line in ("goods_input_electricity_add", "goods_output_electricity_add",
                     "goods_input_grid_power_add", "goods_output_grid_power_add"):
            self.assertRegex(scaled, rf"\b{line} = 1\b", line)


class FlowModifierTest(unittest.TestCase):
    PAIRS = {
        "modifier_grid_station_upload": {"goods_input_electricity_mult", "goods_output_grid_power_mult"},
        "modifier_grid_station_download": {"goods_input_grid_power_mult", "goods_output_electricity_mult"},
    }

    def test_each_modifier_scales_one_direction_at_unit_strength(self):
        text = _code(_read(MODIFIERS))
        for name, pair in self.PAIRS.items():
            lines = dict(re.findall(r"\b(goods_\w+) = (\S+)", _top_level(text, name)))
            self.assertEqual(lines, {line: "1" for line in pair}, name)

    def test_every_grid_power_goods_modifier_is_registered(self):
        types = _read(TYPES)
        for name in ("goods_input_grid_power_add", "goods_output_grid_power_add",
                     "goods_input_grid_power_mult", "goods_output_grid_power_mult",
                     "goods_input_electricity_mult",
                     "state_building_grid_transfer_station_max_level_add",
                     "country_building_grid_transfer_station_require_subsidies_bool"):
            self.assertRegex(types, rf"(?m)^{name} = \{{", name)

    def test_base_values_caps_one_per_state_and_requires_subsidies(self):
        base = _code(_top_level(_read(EXTRA_MODIFIERS), "INJECT:base_values"))
        self.assertRegex(base, r"\bstate_building_grid_transfer_station_max_level_add = 1\b")
        self.assertRegex(base, r"\bcountry_building_grid_transfer_station_require_subsidies_bool = yes\b")

    def test_modifiers_are_applied_with_local_variable_multipliers(self):
        apply = _code(_top_level(_read(EFFECTS), "te_grid_apply_station_modifiers_effect"))
        multipliers = re.findall(r"multiplier = (\S+)", apply)
        self.assertEqual(len(multipliers), 2)
        for value in multipliers:
            self.assertTrue(value.startswith("local_var:"), value)
        for name in self.PAIRS:
            # A same-name add_modifier stacks: the old copy goes first.
            self.assertLess(apply.index(f"remove_modifier = {name}"), apply.index(f"name = {name}"))


class BalancingTest(unittest.TestCase):
    def test_monthly_pulse_runs_the_update(self):
        on_actions = _code(_read(ON_ACTIONS))
        self.assertIn("te_grid_monthly_pulse", _sub(on_actions, "on_monthly_pulse_country"))
        self.assertIn("te_grid_monthly_update_effect = yes", _top_level(on_actions, "te_grid_monthly_pulse"))

    def test_factor_is_measured_before_the_flow_and_order_are_overwritten(self):
        flow = _code(_top_level(_read(EFFECTS), "te_grid_set_station_flow_effect"))
        order = [flow.index(f"name = {name} ") for name in ("te_grid_factor", "te_grid_flow", "te_grid_command")]
        self.assertEqual(order, sorted(order))

    def test_region_is_one_market_area(self):
        trigger = _code(_top_level(_read(TRIGGERS), "te_grid_in_seed_region"))
        self.assertIn("is_in_same_market_area = scope:te_grid_seed", trigger)

    def test_targets_sum_to_zero_over_a_grid(self):
        """te_grid_target_value's formula, LP - LC x P/C, conserves power: the
        same arithmetic over a three-state grid nets to zero."""
        target = _code(_top_level(_read(VALUES), "te_grid_target_value"))
        self.assertIn("value = var:te_grid_local_consumption", target)
        self.assertIn("multiply = owner.var:te_grid_region_production", target)
        self.assertIn("divide = owner.var:te_grid_region_consumption", target)
        self.assertIn("add = var:te_grid_local_production", target)
        states = [(1000, 1000), (0, 1000), (5000, 0)]
        p = sum(s[0] for s in states)
        c = sum(s[1] for s in states)
        targets = [lp - lc * p / c for lp, lc in states]
        self.assertAlmostEqual(sum(targets), 0)
        self.assertGreater(targets[2], 0)
        self.assertLess(targets[1], 0)


class LocalizationTest(unittest.TestCase):
    def test_every_new_key_is_localized(self):
        keys = set()
        for name in os.listdir(LOC_DIR):
            if name.endswith(".yml"):
                keys |= set(re.findall(r"(?m)^ ([\w.]+):\d* ", _read(os.path.join(LOC_DIR, name))))
        for key in ("grid_power", "building_grid_transfer_station", "building_grid_transfer_station_desc",
                    "pmg_grid_transfer_station", "pm_grid_transfer_base",
                    "modifier_grid_station_upload", "modifier_grid_station_download",
                    "te_grid_station_adjacent_tt"):
            self.assertIn(key, keys)


if __name__ == "__main__":
    unittest.main()
