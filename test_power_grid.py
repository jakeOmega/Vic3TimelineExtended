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
EVENTS = os.path.join(REPO, "events", "te_grid_events.txt")
ARTICLE = os.path.join(COMMON, "treaty_articles", "123_grid_interconnection.txt")
TECH_DIR = os.path.join(COMMON, "technology", "technologies")
STATES_PANEL = os.path.join(REPO, "gui", "states_panel.gui")
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
        self.assertEqual(groups, ["pmg_grid_transfer_station", "pmg_grid_interconnector", "pmg_maintenance_heavy"])
        self.assertIn("pm_grid_transfer_base", _sub(_read(PMGS), "production_methods"))
        # The interconnector group's first method, the default, is the one that does nothing.
        methods = _sub(_top_level(_read(PMGS), "pmg_grid_interconnector"), "production_methods").split()
        self.assertEqual(methods, ["pm_grid_no_interconnector", "pm_grid_hvdc_interconnector"])
        hvdc = _code(_top_level(_read(PMS), "pm_grid_hvdc_interconnector"))
        self.assertIn("clean_energy_technologies", _sub(hvdc, "unlocking_technologies"))

    def test_possible_allows_the_own_state_a_neighbour_and_a_first_station(self):
        possible = _sub(self.building, "possible")
        self.assertIn("any_neighbouring_state", possible)
        self.assertIn("is_in_same_market_area = ROOT", possible)
        # Every branch counts a queued station, which has_building misses until it is built.
        self.assertNotIn("has_building", possible)
        self.assertEqual(possible.count("te_grid_state_has_station = yes"), 3)
        trigger = _code(_top_level(_read(TRIGGERS), "te_grid_state_has_station"))
        self.assertIn("any_scope_building", trigger)
        self.assertIn("is_building_type = building_grid_transfer_station", trigger)

    def test_has_a_panel_background(self):
        self.assertRegex(self.building, r'background = "gfx/interface/icons/building_icons/backgrounds/\w+\.dds"')


class MethodTest(unittest.TestCase):
    def test_base_method_carries_one_unit_of_each_line(self):
        scaled = _sub(_top_level(_read(PMS), "pm_grid_transfer_base"), "workforce_scaled")
        for line in ("goods_input_electricity_add", "goods_output_electricity_add",
                     "goods_input_grid_power_add", "goods_output_grid_power_add"):
            self.assertRegex(scaled, rf"\b{line} = 1\b", line)


class FlowModifierTest(unittest.TestCase):
    # One line each, so the Electricity lines can be netted of other bonuses.
    LINES = {
        "modifier_grid_station_upload": "goods_output_grid_power_mult",
        "modifier_grid_station_upload_electricity": "goods_input_electricity_mult",
        "modifier_grid_station_download": "goods_input_grid_power_mult",
        "modifier_grid_station_download_electricity": "goods_output_electricity_mult",
    }

    def test_each_modifier_scales_one_line_at_unit_strength(self):
        text = _code(_read(MODIFIERS))
        for name, line in self.LINES.items():
            lines = dict(re.findall(r"\b(goods_\w+) = (\S+)", _top_level(text, name)))
            self.assertEqual(lines, {line: "1"}, name)

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
        apply = _code(_top_level(_read(EFFECTS), "te_grid_set_station_modifiers_effect"))
        multipliers = re.findall(r"multiplier = (\S+)", apply)
        self.assertEqual(len(multipliers), 4)
        for value in multipliers:
            self.assertTrue(value.startswith("local_var:"), value)
        for name in self.LINES:
            # A same-name add_modifier stacks: the old copy goes first.
            self.assertLess(apply.index(f"remove_modifier = {name}\n"), apply.index(f"name = {name}\n"))

    def test_electricity_lines_are_netted_of_other_bonuses(self):
        effects = _code(_read(EFFECTS))
        apply = _top_level(effects, "te_grid_apply_station_modifiers_effect")
        self.assertIn("subtract = local_var:te_grid_other_input", apply)
        self.assertIn("subtract = local_var:te_grid_other_output", apply)
        # The netting reads last month's total before overwriting what was applied.
        self.assertLess(apply.index("te_grid_read_other_electricity_effect = yes"),
                        apply.index("name = te_grid_upload_electricity_mult value"))
        read = _top_level(effects, "te_grid_read_other_electricity_effect")
        self.assertIn("prev.modifier:goods_input_electricity_mult", read)
        self.assertIn("prev.modifier:goods_output_electricity_mult", read)
        self.assertIn("subtract = var:te_grid_upload_electricity_mult", read)
        self.assertIn("subtract = var:te_grid_download_electricity_mult", read)


class BalancingTest(unittest.TestCase):
    def test_global_pulse_dispatches_one_hidden_country_event(self):
        on_actions = _code(_read(ON_ACTIONS))
        # One world-wide run a month: a country pulse as well would balance every grid twice.
        self.assertNotIn("on_monthly_pulse_country", on_actions)
        self.assertIn("te_grid_world_dispatch", _sub(on_actions, "on_monthly_pulse"))
        dispatch = _top_level(on_actions, "te_grid_world_dispatch")
        self.assertIn("random_country", dispatch)
        self.assertIn("trigger_event = { id = te_grid.1 }", dispatch)
        event = _code(_top_level(_read(EVENTS), "te_grid.1"))
        self.assertRegex(event, r"\bhidden = yes\b")
        self.assertIn("te_grid_world_update_effect = yes", _sub(event, "immediate"))

    def test_run_clears_its_lists_at_both_ends(self):
        effects = _code(_read(EFFECTS))
        run = _top_level(effects, "te_grid_world_update_effect")
        self.assertEqual(run.count("te_grid_world_clear_effect = yes"), 2)
        self.assertLess(run.index("te_grid_world_clear_effect = yes"), run.index("every_country"))
        clear = _top_level(effects, "te_grid_world_clear_effect")
        for name in ("te_grid_pending_states", "te_grid_region", "te_grid_frontier"):
            self.assertIn(f"clear_global_variable_list = {name}", clear)

    def test_factor_is_measured_before_the_flow_and_order_are_overwritten(self):
        balance = _code(_top_level(_read(EFFECTS), "te_grid_balance_region_effect"))
        self.assertLess(balance.index("name = te_grid_factor "), balance.index("name = te_grid_flow "))
        flow = _code(_top_level(_read(EFFECTS), "te_grid_set_station_flow_effect"))
        self.assertIn("name = te_grid_command ", flow)

    def test_a_group_is_one_owner_in_one_market_area(self):
        group = _code(_top_level(_read(EFFECTS), "te_grid_add_group_effect"))
        self.assertIn("owner = {", group)
        self.assertIn("is_in_same_market_area = scope:te_grid_group_of", group)

    def test_links_read_the_partner_list_not_the_treaties(self):
        triggers = _code(_read(TRIGGERS))
        self.assertNotIn("any_scope_treaty", triggers)
        self.assertIn("is_target_in_variable_list = { name = te_grid_partners", triggers)
        refresh = _code(_top_level(_read(EFFECTS), "te_grid_refresh_partners_effect"))
        self.assertIn("has_type = grid_interconnection_agreement", refresh)
        # Between two countries, a link also takes one market (Grid Power is priced per market).
        sea = _top_level(triggers, "te_grid_sea_link")
        self.assertIn("market = $FROM$.market", sea)
        land = _top_level(triggers, "te_grid_land_link")
        self.assertIn("is_in_same_market_area = $FROM$", land)

    @staticmethod
    def solve(states, passes=4):
        """The balancing's ratio and targets, as te_grid_balance_region_effect
        computes them: lossless P / C, then `passes` re-solves of
        r = (sum_up LP + sum_down LP/eff) / (sum_up LC + sum_down LC/eff)."""
        r = sum(lp for lp, _, _ in states) / sum(lc for _, lc, _ in states)
        for _ in range(passes):
            num = den = 0.0
            for lp, lc, eff in states:
                if lp - lc * r > 0:
                    num, den = num + lp, den + lc
                else:
                    num, den = num + lp / eff, den + lc / eff
            r = num / den
        targets = []
        for lp, lc, eff in states:
            surplus = lp - lc * r
            targets.append(surplus if surplus > 0 else surplus / eff)
        return r, targets

    def test_the_value_files_hold_the_modelled_formula(self):
        values = _code(_read(VALUES))
        self.assertIn("multiply = global_var:te_grid_ratio", _top_level(values, "te_grid_surplus_value"))
        target = _top_level(values, "te_grid_target_value")
        self.assertIn("value = te_grid_surplus_value", target)
        self.assertIn("divide = var:te_grid_efficiency", target)
        balance = _code(_top_level(_read(EFFECTS), "te_grid_balance_region_effect"))
        self.assertIn("count = 4", balance)
        self.assertIn("add = te_grid_production_over_efficiency", balance)
        self.assertIn("add = te_grid_consumption_over_efficiency", balance)

    def test_lossless_grid_conserves_and_equalises(self):
        states = [(1000, 1000, 1.0), (0, 1000, 1.0), (5000, 0, 1.0)]
        r, targets = self.solve(states)
        self.assertAlmostEqual(sum(targets), 0)
        self.assertGreater(targets[2], 0)
        self.assertLess(targets[1], 0)

    def test_lossy_grid_conserves_grid_power_and_equalises_supply(self):
        # Two surplus states, two short ones at different efficiencies.
        states = [(4000, 1000, 0.8), (1500, 1000, 0.8), (200, 2000, 0.6), (0, 500, 0.95)]
        r, targets = self.solve(states)
        self.assertAlmostEqual(sum(targets), 0, places=6)
        for (lp, lc, eff), t in zip(states, targets):
            # A sender keeps LP - t; a receiver gets t's Grid Power less its losses.
            supply = lp - t if t > 0 else lp - t * eff
            self.assertAlmostEqual(supply / lc, r, places=6)
        # Losses leave the grid less than its lossless ratio.
        self.assertLess(r, sum(s[0] for s in states) / sum(s[1] for s in states))


class EfficiencyTest(unittest.TestCase):
    def test_efficiency_is_registered_and_starts_low(self):
        self.assertRegex(_read(TYPES), r"(?m)^country_grid_transmission_efficiency_add = \{")
        base = _code(_top_level(_read(EXTRA_MODIFIERS), "INJECT:base_values"))
        self.assertRegex(base, r"\bcountry_grid_transmission_efficiency_add = 0\.6\b")

    STEPS = {"rural_electrification": 0.2, "transistors": 0.05, "clean_energy_technologies": 0.05,
             "smart_grids": 0.05, "modern_material_science": 0.05}

    def test_five_technologies_raise_it_to_one(self):
        found = {}
        for name in sorted(os.listdir(TECH_DIR)):
            text = _code(_read(os.path.join(TECH_DIR, name)))
            for tech in self.STEPS:
                if re.search(rf"(?m)^{tech} = \{{", text):
                    m = re.search(r"country_grid_transmission_efficiency_add = ([\d.]+)", _top_level(text, tech))
                    found[tech] = float(m.group(1))
        self.assertEqual(found, self.STEPS)
        self.assertAlmostEqual(0.6 + sum(found.values()), 1.0)


class TreatyAndTileTest(unittest.TestCase):
    def test_article_is_mutual_and_needs_one_market(self):
        article = _code(_top_level(_read(ARTICLE), "grid_interconnection_agreement"))
        self.assertRegex(article, r"\bkind = mutual\b")
        self.assertIn("market = scope:other_country.market", _sub(article, "possible"))
        # A root-only proposal chance (treaty_evaluation_scope_audit).
        self.assertNotIn("scope:", _sub(article, "evaluation_chance"))

    def test_hub_is_stored_and_shown_only_when_set(self):
        balance = _code(_top_level(_read(EFFECTS), "te_grid_balance_region_effect"))
        self.assertIn("save_scope_as = te_grid_hub_state", balance)
        self.assertIn("set_variable = { name = te_grid_hub value = scope:te_grid_hub_state }", balance)
        hub = _code(_top_level(_read(VALUES), "te_grid_hub_disp"))
        self.assertIn("exists = var:te_grid_hub", hub)
        panel = _read(STATES_PANEL)
        tile = panel[panel.index("### POWER GRID"):panel.index("### UN MISSION", panel.index("### POWER GRID"))]
        self.assertIn("te_grid_hub_disp", tile)

    def test_tile_reads_only_guarded_values(self):
        panel = _read(STATES_PANEL)
        start = panel.index("### POWER GRID")
        tile = panel[start:panel.index("### UN MISSION", start)]
        values = set(re.findall(r"ScriptValue\('(\w+)'\)", tile))
        self.assertIn("te_grid_tile_shown", values)
        defined = set(re.findall(r"(?m)^(\w+) = \{", _read(VALUES)))
        self.assertLessEqual(values, defined)


class LocalizationTest(unittest.TestCase):
    def test_every_new_key_is_localized(self):
        keys = set()
        for name in os.listdir(LOC_DIR):
            if name.endswith(".yml"):
                keys |= set(re.findall(r"(?m)^ ([\w.]+):\d* ", _read(os.path.join(LOC_DIR, name))))
        for key in ("grid_power", "building_grid_transfer_station", "building_grid_transfer_station_desc",
                    "pmg_grid_transfer_station", "pm_grid_transfer_base",
                    "modifier_grid_station_upload", "modifier_grid_station_download",
                    "modifier_grid_station_upload_electricity", "modifier_grid_station_download_electricity",
                    "te_grid_station_adjacent_tt", "concept_power_grid", "concept_power_grid_desc",
                    "country_grid_transmission_efficiency_add", "pmg_grid_interconnector",
                    "pm_grid_no_interconnector", "pm_grid_hvdc_interconnector",
                    "grid_interconnection_agreement", "grid_interconnection_agreement_desc",
                    "grid_interconnection_agreement_effects_desc", "grid_interconnection_agreement_article_short_desc",
                    "treaty_name_grid_interconnection_treaty", "treaty_name_country_adj_country_adj_power_pool",
                    "TE_STATE_GRID_STATUS", "TE_STATE_GRID_TT", "AI_GRID_STATIONS_MEET"):
            self.assertIn(key, keys)


if __name__ == "__main__":
    unittest.main()
