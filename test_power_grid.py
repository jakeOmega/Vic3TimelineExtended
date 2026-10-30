"""Power grids: the Grid Transfer Station, Grid Power and the balancing.

Static checks on the pieces the engine gives no warning for when they are
wrong: the station's method keeps its 1-unit lines of both goods (the flow
modifiers are _mult modifiers that scale them), each flow modifier scales the
right pair of lines, every Grid Power goods modifier is registered (a mod good
gets none from vanilla), base_values carries the one-per-state cap and the
mandatory subsidy, the modifiers are applied with local-variable multipliers
(a var: or script value there would resolve against the country), and the
monthly pulse is wired. Since cross-market interconnection: Grid Power has a
fixed price, a link between two countries needs no shared market, and a
receiving market's pass-through rides the Grid Power lines only and cancels out
of every readback the balancing takes. Since undersea cable ranges: a cable is
a built HVDC Undersea Interconnector with a range on a coast, technologies only
lengthen it, the build walks the sea far enough that either end's range joins
the two, and cables that reach each other let the agreement be signed. Since
the interconnector became a building of its own: it needs a station in its
state, is offered only on a coast, and the AI builds it rather than switching a
method. Since the Power Grid Connection: the station's method gives its state the
connection, and a station takes part only where its state is connected.

Run: python3 test_power_grid.py
"""
import os
import re
import subprocess
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

    def test_grid_power_has_a_fixed_price(self):
        # A grid that spans markets sells more than it buys in one market and the
        # reverse in the other; at a fixed price that is how the power is paid for.
        self.assertRegex(_code(_top_level(_read(GOODS), "grid_power")), r"\bfixed_price = yes\b")

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
        # The undersea cable is a building of its own (InterconnectorBuildingTest), not a method group here.
        self.assertEqual(groups, ["pmg_grid_transfer_station", "pmg_maintenance_heavy"])
        self.assertIn("pm_grid_transfer_base", _sub(_read(PMGS), "production_methods"))

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


class InterconnectorBuildingTest(unittest.TestCase):
    """The HVDC Undersea Interconnector: a building of its own beside a
    station, one per coastal state, government funded, unlocked by Clean
    Energy Technologies."""

    def setUp(self):
        self.building = _code(_top_level(_read(BUILDING), "building_grid_hvdc_interconnector"))

    def test_one_per_state_and_government_funded(self):
        self.assertRegex(self.building, r"building_group = bg_public_infrastructure\b")
        self.assertRegex(self.building, r"has_max_level = yes")
        self.assertRegex(self.building, r"ignore_stateregion_max_level = yes")
        base = _code(_top_level(_read(EXTRA_MODIFIERS), "INJECT:base_values"))
        self.assertRegex(base, r"\bstate_building_grid_hvdc_interconnector_max_level_add = 1\b")
        self.assertRegex(_read(TYPES), r"(?m)^state_building_grid_hvdc_interconnector_max_level_add = \{")

    def test_unlocked_by_clean_energy_technologies(self):
        self.assertEqual(_sub(self.building, "unlocking_technologies").split(), ["clean_energy_technologies"])

    def test_one_method_group_and_maintenance(self):
        groups = _sub(self.building, "production_method_groups").split()
        self.assertEqual(groups, ["pmg_grid_interconnector", "pmg_maintenance_heavy"])
        methods = _sub(_top_level(_read(PMGS), "pmg_grid_interconnector"), "production_methods").split()
        self.assertEqual(methods, ["pm_grid_hvdc_interconnector"])
        self.assertNotIn("pm_grid_no_interconnector", _code(_read(PMS)))

    def test_offered_on_a_coast_beside_a_station(self):
        self.assertIn("is_coastal = yes", _sub(self.building, "potential"))
        possible = _sub(self.building, "possible")
        self.assertIn("text = te_grid_hvdc_needs_station_tt", possible)
        # Built or queued, as the station's own neighbour rule counts one.
        self.assertIn("te_grid_state_has_station = yes", possible)
        self.assertNotIn("has_building", possible)

    def test_the_construction_ai_leaves_it_to_script(self):
        # Without it, a government building gets the engine's default of 1000.
        self.assertRegex(self.building, r"\bai_value = 0\b")
        ai = _code(_top_level(_read(EFFECTS), "te_grid_ai_interconnectors_effect"))
        self.assertIn("start_building_construction = building_grid_hvdc_interconnector", ai)

    def test_has_a_panel_background_and_an_icon(self):
        self.assertRegex(self.building, r'background = "gfx/interface/icons/building_icons/backgrounds/\w+\.dds"')
        icon = re.search(r'\bicon = "([^"]+)"', self.building).group(1)
        path = os.path.join(REPO, icon)
        if not os.path.exists(path):
            # CI checks out without gfx/; a texture git tracks is there.
            subprocess.run(["git", "ls-files", "--error-unmatch", icon], cwd=REPO, check=True,
                           capture_output=True)


class MethodTest(unittest.TestCase):
    LINES = ("goods_input_electricity_add", "goods_output_electricity_add",
             "goods_input_grid_power_add", "goods_output_grid_power_add")

    def test_base_method_carries_one_unit_of_each_line(self):
        # A station moves its staffing's share whatever the block (2026-10-25), so the
        # lines sit in unscaled and the job is made very attractive to keep it staffed.
        method = _code(_top_level(_read(PMS), "pm_grid_transfer_base"))
        self.assertNotIn("workforce_scaled", method)
        unscaled = _sub(method, "unscaled")
        for line in self.LINES:
            self.assertRegex(unscaled, rf"\b{line} = 1\b", line)
            self.assertNotRegex(_sub(method, "level_scaled"), rf"\b{line}\b", line)
        m = re.search(r"\bbuilding_job_attractiveness_mult = (\S+)", unscaled)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(float(m.group(1)), 1)

    def test_a_built_station_is_online_whatever_its_staffing(self):
        # An empty station keeps its order and modifiers, so it runs from its first hire.
        online = _code(_top_level(_read(TRIGGERS), "te_grid_station_online"))
        self.assertIn("level >= 1", online)
        self.assertNotIn("occupancy", online)

    def test_a_station_that_moved_nothing_keeps_its_factor(self):
        # Measured, an empty week would clamp the factor to 0.2 and the first hire would move 5x.
        factor = _code(_top_level(_read(VALUES), "te_grid_station_factor_value"))
        self.assertIn("te_grid_own_uploaded > 0", factor)
        self.assertIn("te_grid_own_downloaded > 0", factor)
        # An empty station is on its grid but passes nothing through, so a staffed one hosts the import.
        settle = _code(_top_level(_read(EFFECTS), "te_grid_settle_market_effect"))
        self.assertGreaterEqual(settle.count("te_grid_station_staffed = yes"), 6)

    def test_staffing_tally_reads_before_the_order_is_overwritten(self):
        balance = _code(_top_level(_read(EFFECTS), "te_grid_balance_region_effect"))
        self.assertLess(balance.index("te_grid_staffing_selfcheck_effect = yes"),
                        balance.index("name = te_grid_factor "))
        # The experiment's one-off factor reset is gone: the factor is measured every run.
        self.assertNotIn("te_grid_unscaled_armed", balance)
        check = _code(_top_level(_read(EFFECTS), "te_grid_staffing_selfcheck_effect"))
        self.assertIn("has_global_variable = te_grid_staffing_collect", check)
        for band in ("occupancy < 0.25", "occupancy < 0.5", "occupancy < 0.9"):
            self.assertIn(band, check)
        self.assertIn("TE_GRID empty_station", check)
        world = _code(_top_level(_read(EFFECTS), "te_grid_world_update_effect"))
        self.assertLess(world.index("te_grid_staffing_info_start_effect = yes"),
                        world.index("te_grid_balance_region_effect = yes"))
        self.assertLess(world.index("te_grid_balance_region_effect = yes"),
                        world.index("te_grid_staffing_info_end_effect = yes"))
        start = _code(_top_level(_read(EFFECTS), "te_grid_staffing_info_start_effect"))
        self.assertIn("global_var:te_grid_staffing_runs >= 13", start)
        end = _code(_top_level(_read(EFFECTS), "te_grid_staffing_info_end_effect"))
        self.assertIn("TE_GRID staffing", end)
        self.assertIn("set_global_variable = te_grid_staffing_logged", end)
        values = _read(VALUES)
        for name in ("te_grid_st_quarter_g", "te_grid_st_half_g", "te_grid_st_most_g", "te_grid_st_full_g"):
            self.assertRegex(values, rf"(?m)^{name} = \{{", name)
        # Staffing is recorded after the checks read last month's record.
        flow = _code(_top_level(_read(EFFECTS), "te_grid_set_station_flow_effect"))
        self.assertIn("set_variable = te_grid_staffed", flow)
        conservation = _code(_top_level(_read(EFFECTS), "te_grid_conservation_selfcheck_effect"))
        self.assertIn("te_grid_station_staffed_throughout = no", conservation)


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
        # One world-wide run a month: a country pulse that balanced as well would balance every
        # grid twice. The country pulse only runs the AI's station building.
        self.assertEqual(_sub(on_actions, "on_monthly_pulse_country").split(),
                         ["on_actions", "=", "{", "te_grid_ai_build_on_action", "}"])
        ai_pass = _top_level(on_actions, "te_grid_ai_build_on_action")
        self.assertNotIn("te_grid.1", ai_pass)
        self.assertNotIn("te_grid_world_update_effect", ai_pass)
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

    def test_links_between_countries_need_no_shared_market(self):
        triggers = _code(_read(TRIGGERS))
        for name in ("te_grid_sea_link", "te_grid_land_link", "te_grid_ai_interconnector_wanted"):
            link = _top_level(triggers, name)
            self.assertIn("te_grid_owners_interconnected", link, name)
            self.assertNotRegex(link, r"\bmarket = ", name)
        self.assertNotIn("is_in_same_market_area", _top_level(triggers, "te_grid_land_link"))

    # The engine's price for a local good (common/defines/extra_defines.txt;
    # te_grid_price_range and te_grid_buy_sell_max_factor in the values file).
    RANGE, FACTOR = 0.999, 4
    SLOPE = (FACTOR - 1) / RANGE

    @classmethod
    def engine_price(cls, sell, buy):
        """A local good's price over its base, as the engine sets it from a
        state's sell and buy orders: matched against Macedonia's Electricity
        in the 2013 Byzantium save, 19.24 of 30."""
        d = (buy - sell) / min(buy, sell) / (cls.FACTOR - 1)
        return 1 + cls.RANGE * max(-1.0, min(1.0, d))

    @classmethod
    def ratio_at(cls, price):
        """The sell/buy ratio at which the engine prices a local good at
        `price` of its base (te_grid_send_ratio_value, te_grid_receive_ratio_value)."""
        if price < 1:
            return 1 + cls.SLOPE * (1 - price)
        if price > 1:
            return 1 / (1 + cls.SLOPE * (price - 1))
        return 1.0

    @classmethod
    def flows_at(cls, states, q):
        """Each state's flow at the sending price q, in Electricity sent, as
        te_grid_surplus_value reads it: a sender's LP / x(q) - LC, a
        receiver's shortfall at q / eff over eff."""
        send = cls.ratio_at(q)
        out = []
        for lp, lc, eff in states:
            if lp > lc * send:
                out.append(lp / send - lc)
            else:
                receive = cls.ratio_at(min(q / eff, 1 + cls.RANGE))
                out.append(-max(0.0, lc * receive - lp) / eff)
        return out

    @classmethod
    def solve(cls, states, passes=12):
        """The balancing's sending price and targets, as
        te_grid_balance_region_effect computes them: `passes` halvings of the
        engine's price range on the sign of the grid's net flow."""
        lo, hi = 1 - cls.RANGE, 1 + cls.RANGE
        for _ in range(passes):
            mid = (lo + hi) / 2
            if sum(cls.flows_at(states, mid)) > 0:
                hi = mid
            else:
                lo = mid
        q = (lo + hi) / 2
        return q, cls.flows_at(states, q)

    @staticmethod
    def balanced(targets):
        """The targets with the larger side scaled so uploads equal downloads,
        as the balancing does after damping."""
        up = sum(t for t in targets if t > 0)
        down = -sum(t for t in targets if t < 0)
        scale_up = down / up if up > down else 1
        scale_down = up / down if down > up else 1
        return [t * scale_up if t > 0 else t * scale_down for t in targets]

    def prices_after(self, states, flows):
        """Each state's Electricity price over its base once its station moves
        its flow: an upload is a buy order in the sending state, a download's
        Electricity a sell order in the receiving one."""
        out = []
        for (lp, lc, eff), t in zip(states, flows):
            out.append(self.engine_price(lp, lc + t) if t > 0 else self.engine_price(lp - t * eff, lc))
        return out

    def test_engine_price_constants_are_the_mod_defines(self):
        defines = _code(_read(os.path.join(COMMON, "defines", "extra_defines.txt")))
        values = _code(_read(VALUES))
        rng = float(re.search(r"\bPRICE_RANGE\s*=\s*([\d.]+)", defines).group(1))
        factor = float(re.search(r"\bBUY_SELL_DIFF_AT_MAX_FACTOR\s*=\s*([\d.]+)", defines).group(1))
        self.assertEqual((rng, factor), (self.RANGE, self.FACTOR))

        def constant(name):
            return float(re.search(rf"(?m)^{name} = ([\d.]+)", values).group(1))

        self.assertEqual(constant("te_grid_price_range"), rng)
        self.assertEqual(constant("te_grid_buy_sell_max_factor"), factor)
        self.assertAlmostEqual(constant("te_grid_price_floor"), 1 - rng)
        self.assertAlmostEqual(constant("te_grid_price_ceiling"), 1 + rng)

    def test_the_value_files_hold_the_modelled_formula(self):
        values = _code(_read(VALUES))
        surplus = _top_level(values, "te_grid_surplus_value")
        self.assertIn("var:te_grid_local_production > te_grid_send_supply_value", surplus)
        self.assertIn("divide = global_var:te_grid_send_ratio", surplus)
        self.assertIn("value = te_grid_receive_shortfall_value", surplus)
        self.assertIn("divide = var:te_grid_efficiency", surplus)
        # The download is over efficiency once, in the surplus, not again in the target.
        target = _top_level(values, "te_grid_target_value")
        self.assertIn("value = te_grid_surplus_value", target)
        self.assertNotIn("te_grid_efficiency", target)
        # Both branches of the ratio for a sender as for a receiver, at the
        # sending price and at it over the receiver's efficiency.
        send = _top_level(values, "te_grid_send_ratio_value")
        self.assertIn("global_var:te_grid_price < 1", send)
        self.assertIn("global_var:te_grid_price > 1", send)
        self.assertEqual(send.count("multiply = te_grid_price_slope"), 2)
        receive_price = _top_level(values, "te_grid_receive_price_value")
        self.assertIn("divide = var:te_grid_efficiency", receive_price)
        self.assertIn("max = te_grid_price_ceiling", receive_price)
        receive = _top_level(values, "te_grid_receive_ratio_value")
        self.assertEqual(receive.count("multiply = te_grid_price_slope"), 2)
        self.assertIn("divide = {", receive)
        shortfall = _top_level(values, "te_grid_receive_shortfall_value")
        self.assertIn("multiply = te_grid_receive_ratio_value", shortfall)
        self.assertRegex(shortfall, r"min = 0\s*$")
        balance = _code(_top_level(_read(EFFECTS), "te_grid_balance_region_effect"))
        self.assertIn("count = 12", balance)
        self.assertIn("value = te_grid_price_floor", balance)
        self.assertIn("value = te_grid_price_ceiling", balance)
        self.assertIn("add = te_grid_surplus_value", balance)
        self.assertEqual(balance.count("te_grid_set_price_midpoint_effect = yes"), 2)
        mid = _code(_top_level(_read(EFFECTS), "te_grid_set_price_midpoint_effect"))
        self.assertIn("multiply = 0.5", mid)
        self.assertIn("value = te_grid_send_ratio_value", mid)

    def test_the_run_clears_the_price(self):
        clear = _code(_top_level(_read(EFFECTS), "te_grid_world_clear_effect"))
        for name in ("te_grid_ratio", "te_grid_region_active", "te_grid_price", "te_grid_send_ratio"):
            self.assertIn(f"remove_global_variable = {name}\n", clear + "\n")

    def test_a_large_sender_sells_at_the_receivers_price_less_their_losses(self):
        # The 2013 Byzantium grid in miniature: Attica makes 87.5M a week and
        # uses 0.16M; four states make little and use the rest. The solve
        # before 2026-10-30 left Attica at base (its station's purchase was most
        # of its demand) and sent the others five times what they use, at the
        # floor.
        states = [(87.5e6, 0.16e6, 0.98), (0.10e6, 0.85e6, 0.98), (0.015e6, 1.38e6, 0.98),
                  (0.05e6, 9.0e6, 0.98), (0.2e6, 6.0e6, 0.98)]
        _, targets = self.solve(states)
        prices = self.prices_after(states, self.balanced(targets))
        for (lp, lc, eff), t, p in zip(states[1:], targets[1:], prices[1:]):
            self.assertLess(t, 0)
            self.assertAlmostEqual(p * eff, prices[0], delta=0.01)
        self.assertLess(prices[0], 0.75)

    def test_receivers_pay_more_by_their_losses(self):
        # Two senders, two receivers at different efficiencies.
        states = [(4000, 1000, 0.75), (1500, 1000, 0.75), (200, 2000, 0.75), (0, 500, 0.9)]
        q, targets = self.solve(states)
        flows = self.balanced(targets)
        self.assertAlmostEqual(sum(flows), 0, places=6)
        prices = self.prices_after(states, flows)
        self.assertAlmostEqual(prices[0], prices[1], delta=0.005)
        self.assertAlmostEqual(prices[2] * 0.75, prices[0], delta=0.005)
        self.assertAlmostEqual(prices[3] * 0.9, prices[0], delta=0.005)

    def test_a_state_between_the_two_prices_stays_off_the_grid(self):
        # At 75% a state whose own ratio lies between the sending and receiving
        # ones gains nothing from the grid.
        states = [(4000, 1000, 0.75), (0, 2000, 0.75), (1100, 1000, 0.75)]
        q, targets = self.solve(states)
        self.assertLess(self.ratio_at(q / 0.75), 1100 / 1000)
        self.assertGreater(self.ratio_at(q), 1100 / 1000)
        self.assertEqual(targets[2], 0)

    def test_a_short_grid_raises_every_price_together(self):
        # The market is one of orders, not stock: a sending station's purchase
        # bids the sender's price up with the rest, so a short grid evens out
        # above base as a long one does below it.
        states = [(10000, 1000, 0.9), (0, 8000, 0.9), (500, 6000, 0.9)]
        q, targets = self.solve(states)
        flows = self.balanced(targets)
        self.assertGreater(q, 1)
        self.assertGreater(flows[0], 10000 - 1000)
        prices = self.prices_after(states, flows)
        self.assertAlmostEqual(prices[0], q, delta=0.005)
        for p in prices[1:]:
            self.assertAlmostEqual(p * 0.9, prices[0], delta=0.005)

    @classmethod
    def price_at_ratio(cls, x):
        """te_grid_price_at_ratio_value: the engine's price at sell/buy x."""
        if x >= 1:
            return 1 - cls.RANGE * min(1.0, (x - 1) / (cls.FACTOR - 1))
        if x > 0:
            return 1 + cls.RANGE * min(1.0, (1 / x - 1) / (cls.FACTOR - 1))
        return 1 + cls.RANGE

    def test_the_tiles_price_is_the_engines_at_the_ratio_the_flow_sets(self):
        for x in (0.2, 0.28, 0.48, 0.9, 1.0, 1.31, 2.5, 3.7, 6.0):
            self.assertAlmostEqual(self.price_at_ratio(x), self.engine_price(x * 100, 100), places=9)
        for p in (0.05, 0.5, 0.99, 1.0, 1.2, 1.8):
            self.assertAlmostEqual(self.price_at_ratio(self.ratio_at(p)), p, places=9)
        values = _code(_read(VALUES))
        at = _top_level(values, "te_grid_price_at_ratio_value")
        self.assertEqual(at.count("divide = te_grid_price_steps"), 2)
        self.assertEqual(at.count("multiply = te_grid_price_range"), 2)
        self.assertEqual(at.count("max = 1"), 2)
        self.assertIn("divide = var:te_grid_ratio_in", at)
        ratio = _top_level(values, "te_grid_flow_ratio_value")
        self.assertIn("add = var:te_grid_flow", ratio)
        self.assertIn("multiply = var:te_grid_efficiency", ratio)
        target = _code(_top_level(_read(EFFECTS), "te_grid_set_price_target_effect"))
        self.assertIn("value = te_grid_flow_ratio_value", target)
        self.assertIn("value = te_grid_price_at_ratio_value", target)
        self.assertIn("remove_variable = te_grid_ratio_in", target)

    def test_the_price_self_checks_pick_states_that_tell_the_formulas_apart(self):
        triggers = _code(_read(TRIGGERS))
        sender = _top_level(triggers, "te_grid_chk_price_sender")
        lo, hi = (float(x) for x in re.findall(r"te_grid_chk_now_ratio_value [<>]= ([\d.]+)", sender))
        # Between about 0.1 and 0.9 of base: away from the floor and from base.
        self.assertLess(self.price_at_ratio(hi), 0.15)
        self.assertGreater(self.price_at_ratio(lo), 0.85)
        self.assertLess(self.price_at_ratio(lo), 0.95)
        self.assertIn("te_grid_chk_station_share_value >= 0.5", sender)
        above = _top_level(triggers, "te_grid_chk_price_above_base")
        lo, hi = (float(x) for x in re.findall(r"te_grid_chk_now_ratio_value [<>]= ([\d.]+)", above))
        for x in (lo, hi):
            alternative = 1 + self.RANGE * (1 - x) / (self.FACTOR - 1)
            self.assertGreater(self.price_at_ratio(x) - alternative, 0.15)
            self.assertLess(self.price_at_ratio(x), 1 + self.RANGE)

    def test_a_grid_without_demand_or_without_supply_moves_nothing(self):
        for states in ([(1000, 0, 0.9), (500, 0, 0.9)],        # no demand: the grid is inactive
                       [(0, 1000, 0.9), (0, 500, 0.9)],        # no supply: receivers only
                       [(5000, 10, 0.9), (2000, 5, 0.9)]):     # senders only
            if sum(lc for _, lc, _ in states) == 0:
                continue  # te_grid_region_active 0: every target is 0
            _, targets = self.solve(states)
            self.assertEqual(self.balanced(targets), [0.0] * len(states), states)

    def test_lossless_grid_conserves_and_equalises(self):
        states = [(1000, 1000, 1.0), (0, 1000, 1.0), (5000, 0, 1.0)]
        _, targets = self.solve(states)
        flows = self.balanced(targets)
        self.assertAlmostEqual(sum(flows), 0, places=6)
        self.assertGreater(flows[2], 0)
        self.assertLess(flows[1], 0)
        prices = self.prices_after(states, flows)
        for p in prices[:2]:
            self.assertAlmostEqual(p, prices[2], delta=0.005)


class BreakEvenTest(unittest.TestCase):
    """Grid Power is how a grid settles: each station's Grid Power line is its
    flow times the grid's sending price (te_grid_power_rate), so a station
    covers its goods at the prices the balancing aims for, whoever owns it,
    and the grid's Grid Power still balances (2026-10-30)."""

    def setUp(self):
        self.effects = _code(_read(EFFECTS))
        self.values = _code(_read(VALUES))

    @staticmethod
    def accounts(states, q, flows):
        """Each station's goods revenue and cost, in units of the base price,
        at the engine's prices once the flows are moved
        (BalancingTest.prices_after): a sender buys its flow of Electricity at
        its state's price and is paid flow x q of Grid Power at 1; a receiver
        pays flow x q of Grid Power and sells flow x eff of Electricity at its
        state's price."""
        prices = BalancingTest().prices_after(states, flows)
        out = []
        for (_, _, eff), t, p in zip(states, flows, prices):
            if t > 0:
                out.append((t * q, t * p))
            elif t < 0:
                out.append((-t * eff * p, -t * q))
            else:
                out.append((0.0, 0.0))
        return out

    def test_every_station_breaks_even_at_the_balancings_prices(self):
        # The 2013 Byzantium grid in miniature, a short grid above base, and
        # two efficiencies.
        for states in ([(87.5e6, 0.16e6, 0.98), (0.10e6, 0.85e6, 0.98), (0.015e6, 1.38e6, 0.98),
                        (0.05e6, 9.0e6, 0.98), (0.2e6, 6.0e6, 0.98)],
                       [(10000, 1000, 0.9), (0, 8000, 0.9), (500, 6000, 0.9)],
                       [(4000, 1000, 0.75), (1500, 1000, 0.75), (200, 2000, 0.75), (0, 500, 0.9)]):
            q, targets = BalancingTest.solve(states)
            flows = BalancingTest.balanced(targets)
            for revenue, cost in self.accounts(states, q, flows):
                self.assertAlmostEqual(revenue, cost, delta=0.01 * max(1.0, cost), msg=states)
            # Grid Power out (senders' flow x q) equals Grid Power in (receivers').
            sold = sum(t * q for t in flows if t > 0)
            bought = -sum(t * q for t in flows if t < 0)
            self.assertAlmostEqual(sold, bought, delta=1e-6 * max(1.0, sold))

    def test_a_receiver_at_the_price_ceiling_pays_the_gap(self):
        # A grid so short that q passes the ceiling times a receiver's
        # efficiency: its price stops at the ceiling, so it pays more than its
        # power sells for, by D x (q - ceiling x eff), at most a quarter of
        # what it pays at 0.75. On one Grid Power a unit the senders lost
        # more, (q - 1) x U.
        ceiling = 1 + BalancingTest.RANGE
        states = [(3000, 4000, 0.75), (0, 8000, 0.75), (100, 10000, 0.75)]
        q, targets = BalancingTest.solve(states)
        flows = BalancingTest.balanced(targets)
        self.assertGreater(q, ceiling * 0.75)
        accounts = self.accounts(states, q, flows)
        for (_, _, eff), t, (revenue, cost) in zip(states, flows, accounts):
            if t < 0:
                self.assertAlmostEqual(cost - revenue, -t * (q - ceiling * eff), delta=0.01 * cost)
                self.assertLessEqual(cost - revenue, 0.25 * cost + 1e-9)
        loss_now = sum(cost - revenue for revenue, cost in accounts if cost > revenue)
        senders_before = sum(t * (q - 1) for t in flows if t > 0)
        self.assertGreater(senders_before, loss_now)

    def test_a_fixed_unit_grid_power_leaves_the_receivers_in_the_red(self):
        # Before: one Grid Power a unit of flow. At a sending price under base
        # the senders' stations profit and the receivers' lose as much.
        states = [(87.5e6, 0.16e6, 0.98), (0.10e6, 0.85e6, 0.98), (0.05e6, 9.0e6, 0.98)]
        q, targets = BalancingTest.solve(states)
        flows = BalancingTest.balanced(targets)
        self.assertLess(q, 0.75)
        prices = BalancingTest().prices_after(states, flows)
        receivers_loss = sum(-t - (-t * 0.98) * p for t, p in zip(flows, prices) if t < 0)
        self.assertGreater(receivers_loss, 0.3 * -sum(t for t in flows if t < 0))

    def test_electricitys_base_is_grid_powers_cost(self):
        # The rate is the sending price over Electricity's base, in Grid Power
        # at its cost: the two must be the same.
        import json
        vanilla = json.load(open(os.path.join(REPO, "vanilla_parsed", "common", "goods.json"),
                                 encoding="utf-8"))
        electricity = vanilla["electricity"][1]
        self.assertEqual(electricity["cost"][1], "30")
        self.assertRegex(_code(_top_level(_read(GOODS), "grid_power")), r"\bcost = 30\b")
        self.assertNotRegex(_code(_read(GOODS)), r"(?m)^(REPLACE:|INJECT:)?electricity = \{")

    def test_the_grid_power_lines_carry_the_rate_and_the_electricity_lines_do_not(self):
        for name in ("te_grid_upload_power_mult_value", "te_grid_download_mult_value"):
            self.assertIn("multiply = te_grid_power_rate_value", _top_level(self.values, name), name)
        for name in ("te_grid_upload_mult_value", "te_grid_download_supply_mult_value"):
            self.assertNotIn("te_grid_power_rate", _top_level(self.values, name), name)

    def test_the_readbacks_divide_by_the_rate_the_lines_were_set_at(self):
        for name in ("te_grid_uploaded", "te_grid_downloaded"):
            self.assertIn("divide = te_grid_power_rate_value", _top_level(self.values, name), name)
        rate = _top_level(self.values, "te_grid_power_rate_value")
        self.assertRegex(rate, r"^\s*value = 1\b")
        self.assertIn("value = var:te_grid_power_rate", rate)
        # Set at the grid's price before the multipliers are taken, kept while
        # idle (nothing moves) and cleared with the station.
        flow = _top_level(self.effects, "te_grid_set_station_flow_effect")
        self.assertIn("set_variable = { name = te_grid_power_rate value = global_var:te_grid_price }", flow)
        self.assertLess(flow.index("name = te_grid_power_rate"), flow.index("name = te_grid_upload_power_mult"))
        self.assertIn("remove_variable = te_grid_power_rate", _top_level(self.effects, "te_grid_clear_state_effect"))
        # The factor reads last month's rate: the rate is set after it.
        balance = _top_level(self.effects, "te_grid_balance_region_effect")
        self.assertLess(balance.index("name = te_grid_factor "), balance.index("te_grid_set_station_flow_effect = yes"))

    def test_the_tiles_grid_power_figures_carry_the_rate(self):
        for name in ("te_grid_market_flow_disp", "te_grid_import_disp"):
            self.assertIn("multiply = te_grid_power_rate_value", _top_level(self.values, name), name)

    def test_the_rate_self_check_tells_a_scaled_line_from_an_unscaled_one(self):
        check = _top_level(self.effects, "te_grid_power_rate_selfcheck_effect")
        self.assertIn("TE_SELF_CHECK OK grid_power_rate", check)
        self.assertIn("TE_SELF_CHECK BROKEN grid_power_rate", check)
        self.assertIn("has_variable = te_grid_power_rate", check)
        self.assertIn("te_grid_station_staffed_throughout = yes", check)
        self.assertIn("occupancy >= 0.9", check)
        # The throughput read is divided out, so the check judges
        # stations whatever their throughput (#1248: Global Warming's line put
        # every BYZ station outside the old -0.05 to +0.1 window).
        self.assertNotIn("modifier:building_throughput_add", check)
        self.assertIn("divide = te_grid_station_throughput_value",
                      _top_level(self.values, "te_grid_chk_rate_moved_value"))
        # Slack for a read a little off what cut last week's output, within the
        # steady gate (ThroughputTest.test_both_measuring_checks_wait_for_a_steady_read);
        # a strike's group line the read misses (-0.2) would fail the check, as before.
        thr_lo, thr_hi = -0.05, 0.1
        low = float(re.search(r"OR = \{\s*var:te_grid_power_rate <= ([\d.]+)", check).group(1))
        high_lo, high_hi = (float(x) for x in re.search(
            r"AND = \{\s*var:te_grid_power_rate >= ([\d.]+)\s*var:te_grid_power_rate <= ([\d.]+)", check).groups())
        ok_lo = float(re.search(r"te_grid_chk_rate_moved_value >= ([\d.]+)", check).group(1))
        ok_hi = float(re.search(r"te_grid_chk_rate_moved_value <= ([\d.]+)", check).group(1))
        # Below the ceiling, where a sending state nears the shortage threshold.
        self.assertLess(high_hi, 1.95)
        # A correct line reads staffing, times whatever throughput the read
        # misses; one set without the rate reads that over the rate, one with
        # it twice that times the rate. All three apart at any rate chosen.
        for read in (0.9 * (1 + thr_lo), 0.9, 1.0, 1.0 * (1 + thr_hi)):
            self.assertTrue(ok_lo <= read <= ok_hi, read)
            for rate in (low, 0.1, high_lo, high_hi):
                self.assertFalse(ok_lo <= read / rate <= ok_hi, (read, rate))
                self.assertFalse(ok_lo <= read * rate <= ok_hi, (read, rate))
        balance = _top_level(self.effects, "te_grid_balance_region_effect")
        self.assertLess(balance.index("te_grid_power_rate_selfcheck_effect = yes"), balance.index("name = te_grid_factor "))
        self.assertTrue(re.search(r"(?m)^te_grid_chk_rate_moved_value = \{", _read(VALUES)))
        # The state's own Grid Power price, which settlement assumes is base.
        self.assertIn("TE_SELF_CHECK OK grid_power_state_price", check)
        self.assertIn("global_var:te_grid_chk_state_gp_gap <= 0.02", check)
        self.assertIn("sg:grid_power", _top_level(self.values, "te_grid_chk_state_gp_gap_value"))


class EfficiencyTest(unittest.TestCase):
    def test_efficiency_is_registered_and_starts_low(self):
        self.assertRegex(_read(TYPES), r"(?m)^country_grid_transmission_efficiency_add = \{")
        base = _code(_top_level(_read(EXTRA_MODIFIERS), "INJECT:base_values"))
        self.assertRegex(base, r"\bcountry_grid_transmission_efficiency_add = 0\.75\b")

    STEPS = {"rural_electrification": 0.1, "transistors": 0.05, "microprocessor": 0.02,
             "clean_energy_technologies": 0.03, "smart_grids": 0.03, "quantum_materials": 0.02}

    def test_six_technologies_raise_it_to_one(self):
        found = {}
        for name in sorted(os.listdir(TECH_DIR)):
            text = _code(_read(os.path.join(TECH_DIR, name)))
            for tech in self.STEPS:
                if re.search(rf"(?m)^{tech} = \{{", text):
                    m = re.search(r"country_grid_transmission_efficiency_add = ([\d.]+)", _top_level(text, tech))
                    found[tech] = float(m.group(1))
        self.assertEqual(found, self.STEPS)
        self.assertAlmostEqual(0.75 + sum(found.values()), 1.0)


class TreatyAndTileTest(unittest.TestCase):
    def test_article_is_mutual_and_joins_any_two_markets(self):
        article = _code(_top_level(_read(ARTICLE), "grid_interconnection_agreement"))
        self.assertRegex(article, r"\bkind = mutual\b")
        self.assertNotIn("market", _sub(article, "possible"))
        # Nothing breaks it when the two leave each other's market.
        self.assertNotIn("requirement_to_maintain", article)
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


class AITest(unittest.TestCase):
    def test_station_costs_what_barracks_cost(self):
        building = _code(_top_level(_read(BUILDING), "building_grid_transfer_station"))
        self.assertRegex(building, r"\brequired_construction = construction_cost_very_low\b")

    def test_ai_value_asks_for_power_in_the_market_area_not_the_states_own_use(self):
        value = _code(_top_level(_read(VALUES), "te_grid_station_ai_value"))
        self.assertIn("te_grid_ai_market_area_has_power = yes", value)
        # A state without power runs no method that uses it, so its use reads as none.
        self.assertNotIn("consumption", value)
        powered = _code(_top_level(_read(TRIGGERS), "te_grid_ai_market_area_has_power"))
        self.assertIn("is_in_same_market_area = scope:te_grid_ai_powered", powered)
        self.assertIn("te_grid_electricity_production > 0", powered)

    def test_ai_placement_mirrors_the_buildings_possible(self):
        possible = _sub(_code(_top_level(_read(BUILDING), "building_grid_transfer_station")), "possible")
        placeable = _code(_top_level(_read(TRIGGERS), "te_grid_station_placeable"))
        for text in (possible, placeable):
            self.assertIn("any_neighbouring_state", text)
            self.assertIn("is_in_same_market_area", text)
            self.assertNotIn("has_building", text)
        # Not ROOT: the AI's pass runs in country scope.
        self.assertNotIn("ROOT", placeable)
        self.assertEqual(placeable.count("te_grid_state_has_station = yes"), 2)

    def test_ai_queues_one_station_a_month_where_it_ranks_highest(self):
        on_actions = _code(_read(ON_ACTIONS))
        self.assertIn("is_ai = yes", _top_level(on_actions, "te_grid_ai_build_on_action"))
        self.assertIn("te_grid_ai_build_effect = yes", _top_level(on_actions, "te_grid_ai_build_on_action"))
        build = _code(_top_level(_read(EFFECTS), "te_grid_ai_build_effect"))
        self.assertIn("has_technology_researched = electrical_capacitors", build)
        pick = _sub(build, "ordered_scope_state")
        self.assertIn("te_grid_ai_station_site = yes", pick)
        self.assertIn("order_by = te_grid_station_ai_value", pick)
        self.assertEqual(build.count("start_building_construction = building_grid_transfer_station"), 1)
        site = _code(_top_level(_read(TRIGGERS), "te_grid_ai_station_site"))
        for check in ("te_grid_state_has_station = no", "te_grid_ai_market_area_has_power = yes",
                      "te_grid_station_placeable = yes"):
            self.assertIn(check, site)


class CrossMarketTest(unittest.TestCase):
    def setUp(self):
        self.effects = _code(_read(EFFECTS))
        self.values = _code(_read(VALUES))

    def test_markets_settle_after_every_flow_is_set_and_before_the_orders(self):
        balance = _top_level(self.effects, "te_grid_balance_region_effect")
        settle = balance.index("te_grid_cross_market_effect = yes")
        self.assertLess(balance.rindex("name = te_grid_flow value = var:te_grid_next_flow"), settle)
        self.assertLess(settle, balance.index("te_grid_set_station_flow_effect = yes"))
        # The self-checks read last month's pass-through before it is overwritten.
        for check in ("te_grid_import_selfcheck_effect", "te_grid_fixed_price_selfcheck_effect"):
            self.assertLess(balance.index(f"{check} = yes"), settle)

    def test_only_a_receiving_market_passes_its_import_through(self):
        settle = _top_level(self.effects, "te_grid_settle_market_effect")
        self.assertIn("change_local_variable = { name = te_grid_market_sum add = var:te_grid_flow }", settle)
        self.assertIn("set_variable = { name = te_grid_import value = 0 }", settle)
        tail = settle[settle.rindex("limit = { local_var:te_grid_market_sum < 0 }"):]
        self.assertIn("scope:te_grid_import_host", tail)
        self.assertIn("change_variable = { name = te_grid_import multiply = -1 }", tail)
        # A grid within one market, an idle station and a gone one keep no pass-through.
        clear = _top_level(self.effects, "te_grid_clear_cross_market_effect")
        for name in ("te_grid_import", "te_grid_market_net"):
            self.assertIn(f"remove_variable = {name}", clear)
        for caller in ("te_grid_idle_station_effect", "te_grid_clear_state_effect"):
            self.assertIn("te_grid_clear_cross_market_effect = yes", _top_level(self.effects, caller))

    def test_pass_through_rides_the_grid_power_lines_only(self):
        for name in ("te_grid_upload_power_mult_value", "te_grid_download_mult_value"):
            self.assertIn("add = var:te_grid_import_command", _top_level(self.values, name), name)
        for name in ("te_grid_upload_mult_value", "te_grid_download_supply_mult_value"):
            self.assertNotIn("te_grid_import", _top_level(self.values, name), name)
        apply = _top_level(self.effects, "te_grid_set_station_modifiers_effect")
        self.assertRegex(apply, r"name = modifier_grid_station_upload\n\s*multiplier = local_var:te_grid_upload_power_mult\b")
        self.assertRegex(apply, r"name = modifier_grid_station_upload_electricity\n\s*multiplier = local_var:te_grid_upload_electricity_mult\b")
        # Every path that applies the modifiers sets the Grid Power out multiplier.
        for caller in ("te_grid_set_station_flow_effect", "te_grid_idle_station_effect"):
            self.assertIn("name = te_grid_upload_power_mult", _top_level(self.effects, caller), caller)

    def test_readbacks_leave_the_pass_through_out(self):
        # A pass-through adds the same to both Grid Power lines, so the difference is
        # the station's own flow.
        self.assertIn("subtract = te_grid_downloaded", _top_level(self.values, "te_grid_own_uploaded"))
        self.assertIn("subtract = te_grid_uploaded", _top_level(self.values, "te_grid_own_downloaded"))
        for name in ("te_grid_local_production_value", "te_grid_local_consumption_value",
                     "te_grid_station_factor_value"):
            body = _top_level(self.values, name)
            self.assertNotRegex(body, r"\bte_grid_(up|down)loaded\b", name)
            self.assertRegex(body, r"\bte_grid_own_(up|down)loaded\b", name)
        verdict = _top_level(self.effects, "te_grid_conservation_verdict_effect")
        self.assertNotRegex(verdict, r"\badd = te_grid_(up|down)loaded\b")

    @staticmethod
    def settle(members):
        """Per market, the net Grid Power its members on the grid move (+ sent),
        and the pass-through the balancing gives a receiving market."""
        nets = {}
        for market, flow in members:
            nets[market] = nets.get(market, 0.0) + flow
        return nets, {m: -n for m, n in nets.items() if n < 0}

    def test_a_spanning_grid_crosses_what_one_market_sends_and_another_receives(self):
        # Market A has the plants; market B's two states have none. The
        # market settlement runs on the flows, once the larger side is scaled.
        states = [(5000, 1000, 0.9, "A"), (800, 1000, 0.9, "A"), (0, 1500, 0.8, "B"), (100, 900, 0.8, "B")]
        _, targets = BalancingTest.solve([(lp, lc, eff) for lp, lc, eff, _ in states])
        targets = BalancingTest.balanced(targets)
        nets, passes = self.settle([(m, t) for (_, _, _, m), t in zip(states, targets)])
        self.assertAlmostEqual(sum(nets.values()), 0, places=6)
        self.assertGreater(nets["A"], 0)
        self.assertEqual(set(passes), {"B"})
        # B sells nothing of its own; with its pass-through it sells half what it buys.
        sold = sum(t for (_, _, _, m), t in zip(states, targets) if m == "B" and t > 0) + passes["B"]
        bought = -sum(t for (_, _, _, m), t in zip(states, targets) if m == "B" and t < 0) + passes["B"]
        self.assertGreaterEqual(sold / bought, 0.5 - 1e-9)


class CableRangeTest(unittest.TestCase):
    """Undersea cables: a built HVDC Undersea Interconnector lays a cable,
    whose method gives a range of one Sea Node, which Smart Grids and Quantum
    Materials lengthen."""

    SGUIS = os.path.join(COMMON, "scripted_guis", "te_grid_sguis.txt")

    def test_range_is_a_script_only_building_type(self):
        body = _code(_top_level(_read(TYPES), "building_grid_undersea_cable_range_add"))
        self.assertRegex(body, r"\bscript_only = yes\b")
        self.assertRegex(body, r"\bdecimals = 0\b")
        self.assertRegex(body, r"\bpercent = no\b")

    def test_the_building_is_the_cable(self):
        # The Undersea Cable boolean marked which station's method laid one; the building does now.
        for path in (TYPES, PMS, TRIGGERS, VALUES, EFFECTS):
            self.assertNotIn("building_grid_undersea_cable_bool", _code(_read(path)), path)

    def test_method_gives_one_and_the_ai_reckons_with_the_same(self):
        hvdc = _code(_top_level(_read(PMS), "pm_grid_hvdc_interconnector"))
        m = re.search(r"\bbuilding_grid_undersea_cable_range_add = (\d+)", _sub(hvdc, "unscaled"))
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "1")
        ai = re.search(r"(?m)^te_grid_hvdc_method_range = (\d+)", _code(_read(VALUES)))
        self.assertIsNotNone(ai)
        self.assertEqual(ai.group(1), m.group(1))

    def test_a_cable_is_the_cable_and_a_range_on_a_coast_not_the_method(self):
        triggers = _code(_read(TRIGGERS))
        has = _top_level(triggers, "te_grid_has_interconnector")
        self.assertIn("is_coastal = yes", has)
        # A technology's range lengthens a cable; only the cable modifier lays one.
        self.assertIn("te_grid_lays_cable = yes", has)
        self.assertIn("te_grid_cable_range_value >= 1", has)
        self.assertNotIn("has_active_production_method", has)
        # Built: one queued exists at level 0 and lays nothing yet.
        lays = _top_level(triggers, "te_grid_lays_cable")
        self.assertIn("is_building_type = building_grid_hvdc_interconnector", lays)
        self.assertIn("level >= 1", lays)
        self.assertNotIn("has_active_production_method", triggers)
        value = _code(_top_level(_read(VALUES), "te_grid_cable_range_value"))
        self.assertIn("is_building_type = building_grid_hvdc_interconnector", value)
        self.assertIn("add = modifier:building_grid_undersea_cable_range_add", value)

    def test_either_end_reaches(self):
        in_range = _code(_top_level(_read(TRIGGERS), "te_grid_cable_in_range"))
        self.assertIn("var:te_grid_sea_hops <= local_var:te_grid_cable_from_range", in_range)
        self.assertIn("var:te_grid_sea_hops <= te_grid_cable_range_value", in_range)

    def test_expansion_walks_the_sea_to_the_longest_cable_of_the_run(self):
        effects = _code(_read(EFFECTS))
        expand = _top_level(effects, "te_grid_expand_from_effect")
        self.assertIn("te_grid_cable_links_effect = yes", expand)
        self.assertNotIn("every_sea_node_adjacent_state", expand)
        links = _top_level(effects, "te_grid_cable_links_effect")
        # Not the station's own range: one whose cable is shorter still joins one whose cable reaches it.
        self.assertIn("name = te_grid_sea_radius value = global_var:te_grid_cable_range_max", links)
        self.assertLess(links.index("te_grid_sea_reach_effect = yes"), links.index("te_grid_sea_reach_clear_effect = yes"))
        for check in ("te_grid_sea_link = { FROM = scope:te_grid_link_from }", "te_grid_cable_in_range = yes",
                      "has_variable = te_grid_member", "te_grid_add_group_effect = yes"):
            self.assertIn(check, links)
        run = _top_level(effects, "te_grid_world_update_effect")
        self.assertIn("set_global_variable = { name = te_grid_cable_range_max value = 0 }", run)
        self.assertIn("set_global_variable = { name = te_grid_cable_range_max value = te_grid_cable_range_value }", run)
        self.assertLess(run.index("te_grid_cable_range_max value = 0"), run.index("while"))
        clear = _top_level(effects, "te_grid_world_clear_effect")
        self.assertIn("remove_global_variable = te_grid_cable_range_max", clear)
        self.assertIn("te_grid_sea_reach_clear_effect = yes", clear)

    def test_the_walk_marks_each_state_once_and_clears_after_itself(self):
        effects = _code(_read(EFFECTS))
        walk = _top_level(effects, "te_grid_sea_reach_effect")
        self.assertTrue(walk.lstrip().startswith("te_grid_sea_reach_clear_effect = yes"))
        self.assertIn("local_var:te_grid_sea_hop < local_var:te_grid_sea_radius", _sub(walk, "while"))
        hop = _sub(_sub(walk, "while"), "every_sea_node_adjacent_state")
        self.assertIn("NOT = { has_variable = te_grid_sea_hops }", hop)
        self.assertIn("name = te_grid_sea_hops value = local_var:te_grid_sea_hop", hop)
        clear = _top_level(effects, "te_grid_sea_reach_clear_effect")
        self.assertIn("remove_variable = te_grid_sea_hops", clear)
        for name in ("te_grid_sea_reach", "te_grid_sea_layer", "te_grid_sea_next"):
            self.assertIn(f"clear_global_variable_list = {name}", clear)
        # No trigger walks the sea by nesting any_sea_node_adjacent_state, which grows as 30^k.
        self.assertNotIn("any_sea_node_adjacent_state", _code(_read(TRIGGERS)))

    def test_the_ai_reckons_its_reach_with_the_method(self):
        ai = _code(_top_level(_read(EFFECTS), "te_grid_ai_interconnectors_effect"))
        self.assertIn("name = te_grid_sea_radius value = te_grid_ai_cable_reach_value", ai)
        reach = _code(_top_level(_read(VALUES), "te_grid_ai_cable_reach_value"))
        self.assertIn("te_grid_lays_cable = no", reach)
        self.assertIn("value = te_grid_hvdc_method_range", reach)
        # Technology's share, read from the station: a state without an interconnector has no read of its own.
        self.assertIn("add = te_grid_tech_cable_range_value", reach)
        tech = _code(_top_level(_read(VALUES), "te_grid_tech_cable_range_value"))
        self.assertIn("is_building_type = building_grid_transfer_station", tech)
        self.assertLess(ai.index("te_grid_sea_reach_effect = yes"), ai.index("te_grid_ai_interconnector_wanted = yes"))
        self.assertIn("te_grid_sea_reach_clear_effect = yes", ai)
        wanted = _code(_top_level(_read(TRIGGERS), "te_grid_ai_interconnector_wanted"))
        self.assertIn("variable = te_grid_sea_reach", wanted)
        # The walk grows with range, so a station is judged twice a year, not monthly.
        self.assertIn("NOT = { has_variable = te_grid_ai_hvdc_checked }", ai)
        self.assertIn("set_variable = { name = te_grid_ai_hvdc_checked value = yes days = 180 }", ai)

    def test_the_ai_builds_one_a_month_and_switches_no_method(self):
        ai = _code(_top_level(_read(EFFECTS), "te_grid_ai_interconnectors_effect"))
        self.assertNotIn("activate_production_method", ai)
        self.assertEqual(ai.count("start_building_construction"), 1)
        self.assertIn("te_grid_state_has_interconnector = no", ai)
        # One a month, none while another is still being built, and only on a short government queue.
        self.assertIn("name = te_grid_ai_hvdc_queued value = 1", ai)
        self.assertLess(ai.index("local_var:te_grid_ai_hvdc_queued = 0"), ai.index("te_grid_sea_reach_effect = yes"))
        self.assertIn("level < 1", ai)
        self.assertIn("construction_queue_government_duration < 52", ai)
        self.assertIn("in_default = no", ai)
        has = _code(_top_level(_read(TRIGGERS), "te_grid_state_has_interconnector"))
        self.assertIn("is_building_type = building_grid_hvdc_interconnector", has)
        self.assertNotIn("level", has)

    def test_cable_links_are_rebuilt_each_run(self):
        effects = _code(_read(EFFECTS))
        run = _top_level(effects, "te_grid_world_update_effect")
        self.assertIn("clear_variable_list = te_grid_cable_links", run)
        self.assertLess(run.index("clear_variable_list = te_grid_cable_links"), run.index("while"))
        self.assertIn("clear_variable_list = te_grid_cable_links", _top_level(effects, "te_grid_clear_state_effect"))
        add = _top_level(effects, "te_grid_add_cable_link_effect")
        self.assertEqual(add.count("is_target_in_variable_list = { name = te_grid_cable_links"), 2)
        # A cable within one group is not what joins it.
        links = _top_level(effects, "te_grid_cable_links_effect")
        self.assertIn("is_in_same_market_area = scope:te_grid_link_from", links)

    def test_self_check_reads_the_methods_range(self):
        effects = _code(_read(EFFECTS))
        self.assertIn("te_grid_cable_range_selfcheck_effect = yes", _top_level(effects, "te_grid_world_update_effect"))
        check = _top_level(_read(EFFECTS), "te_grid_cable_range_selfcheck_effect")
        self.assertIn("te_grid_lays_cable = yes", check)
        # Net of technology, so Smart Grids can't pass for the method's line.
        self.assertIn("te_grid_chk_method_range_value >= te_grid_hvdc_method_range", check)
        # A run after it is first seen built, so its modifiers have settled.
        self.assertLess(check.index("has_variable = te_grid_chk_cable_seen"), check.index("TE_SELF_CHECK OK"))
        self.assertIn("set_variable = { name = te_grid_chk_cable_seen value = yes days = 45 }", check)
        net = _code(_top_level(_read(VALUES), "te_grid_chk_method_range_value"))
        self.assertIn("value = te_grid_cable_range_value", net)
        self.assertIn("subtract = te_grid_tech_cable_range_value", net)
        self.assertIn("TE_SELF_CHECK OK grid_cable_range", check)
        self.assertIn("TE_SELF_CHECK BROKEN grid_cable_range", check)

    RANGE_TECHS = {"smart_grids": 1, "quantum_materials": 1}

    def test_smart_grids_and_quantum_materials_lengthen_the_cable(self):
        found = {}
        for name in sorted(os.listdir(TECH_DIR)):
            text = _code(_read(os.path.join(TECH_DIR, name)))
            for m in re.finditer(r"(?m)^(\w+) = \{", text):
                body = _block_from(text, m.end())
                r = re.search(r"\bbuilding_grid_undersea_cable_range_add = (\d+)", body)
                if r:
                    found[m.group(1)] = int(r.group(1))
        self.assertEqual(found, self.RANGE_TECHS)

    def test_agreement_reads_the_cables_that_reach_each_other(self):
        effects = _code(_read(EFFECTS))
        run = _top_level(effects, "te_grid_world_update_effect")
        self.assertIn("clear_variable_list = te_grid_cable_reach", run)
        self.assertLess(run.index("clear_variable_list = te_grid_cable_reach"), run.index("while"))
        links = _top_level(effects, "te_grid_cable_links_effect")
        self.assertIn("te_grid_add_cable_reach_effect = yes", links)
        # Any other country's cable in range, partner or not: that is what lets the two sign.
        reach_pass = links[links.rindex("every_in_global_list"):]
        self.assertIn("NOT = { owner = scope:te_grid_link_from.owner }", reach_pass)
        self.assertIn("te_grid_cable_in_range = yes", reach_pass)
        self.assertNotIn("te_grid_sea_link", reach_pass)
        add = _top_level(effects, "te_grid_add_cable_reach_effect")
        self.assertEqual(add.count("is_target_in_variable_list = { name = te_grid_cable_reach"), 2)
        article = _code(_top_level(_read(ARTICLE), "grid_interconnection_agreement"))
        self.assertIn("is_target_in_variable_list = { name = te_grid_cable_reach target = scope:other_country }",
                      _sub(article, "possible"))
        self.assertIn("is_target_in_variable_list = { name = te_grid_cable_reach target = scope:te_treaty_partner }",
                      _sub(article, "inherent_accept_score"))

    def test_tile_has_a_sea_cables_row_naming_the_links(self):
        panel = _read(STATES_PANEL)
        start = panel.index("### POWER GRID")
        tile = panel[start:panel.index("### UN MISSION", start)]
        self.assertIn("TE_STATE_GRID_ROW_CABLES_TT", tile)
        self.assertIn("te_grid_cable_count_disp", tile)
        sgui = _code(_top_level(_read(self.SGUIS), "te_grid_cable_links_sgui"))
        self.assertRegex(sgui, r"\bscope = state\b")
        self.assertIn("variable = te_grid_cable_links", _sub(sgui, "every_in_list"))
        loc = _read(os.path.join(LOC_DIR, "te_miscellaneous_l_english.yml"))
        tt = re.search(r"(?m)^ TE_STATE_GRID_ROW_CABLES_TT:0 (.*)$", loc).group(1)
        self.assertIn("GetScriptedGui('te_grid_cable_links_sgui').ExecuteTooltip(GuiScope.SetRoot(State.MakeScope).End)", tt)

    @staticmethod
    def grids(edges, ranges, seed_order):
        """The grids the build makes on a toy sea: `edges` are pairs of states
        sharing a Sea Node, `ranges` each station's range (all have a cable).
        Each member walks out to the run's longest range and joins a station
        within either end's range, as te_grid_cable_links_effect does."""
        nbrs = {}
        for a, b in edges:
            nbrs.setdefault(a, set()).add(b)
            nbrs.setdefault(b, set()).add(a)
        radius = max(ranges.values())

        def hops_from(start):
            hops, layer = {start: 0}, [start]
            for hop in range(1, radius + 1):
                nxt = []
                for s in layer:
                    for n in sorted(nbrs.get(s, ())):
                        if n not in hops:
                            hops[n] = hop
                            nxt.append(n)
                layer = nxt
            return hops

        pending, out = [s for s in seed_order if s in ranges], []
        while pending:
            region, frontier = {pending[0]}, [pending.pop(0)]
            while frontier:
                x = frontier.pop(0)
                for y, d in hops_from(x).items():
                    if y in pending and (d <= ranges[x] or d <= ranges[y]):
                        pending.remove(y)
                        region.add(y)
                        frontier.append(y)
            out.append(frozenset(region))
        return set(out)

    def test_the_grids_do_not_depend_on_the_seed(self):
        # A - c - B - d - C along a coast: A and C two hops from B, four from each other.
        edges = [("A", "c"), ("c", "B"), ("B", "d"), ("d", "C")]
        ranges = {"A": 1, "B": 2, "C": 1}
        first = self.grids(edges, ranges, ["A", "B", "C"])
        self.assertEqual(first, {frozenset("ABC")})
        self.assertEqual(self.grids(edges, ranges, ["C", "A", "B"]), first)
        # With every range 1, as the method alone gives, two hops is too far.
        self.assertEqual(self.grids(edges, {"A": 1, "B": 1, "C": 1}, ["A", "B", "C"]),
                         {frozenset("A"), frozenset("B"), frozenset("C")})


class ThroughputTest(unittest.TestCase):
    """A station's lines move its throughput's share of what they are set to
    (1 plus its building's building_throughput_add read, which carries the
    country's lines, Global Warming's among them). The factor is measured over
    the read, so it holds staffing and shortages only (#1248: every BYZ
    station's factor sat at 0.955 in 2013, 1 less the warming line at 1.81 C),
    and the order is divided by it. A running station's order stays what it
    was: a step earlier in the month is in last week's output already, and a
    first build that measured over the read the last order was set for counted
    it twice (review of #1253)."""

    def setUp(self):
        self.effects = _code(_read(EFFECTS))
        self.values = _code(_read(VALUES))

    @staticmethod
    def model(weekly, staffing=1.0, idle=(), factor=1.0, stored=True, read_based=True, flow=1000.0):
        """What a station moves of its flow each week, by the values' formulas,
        and its factor at the end. weekly[m] is the throughput its lines run at
        in each week of month m (the read at month m's run is weekly[m][0]);
        idle, the months it is ordered nothing; factor, its factor before the
        first run, and stored, whether a read came with it (False: a save from
        before #1248, whose factor carries its throughput). read_based=False is
        the build before: the factor is moved over ordered, and the order the
        flow over it."""
        shares = []
        command = moved = None
        for month, weeks in enumerate(weekly):
            read = max(0.2, 1 + weeks[0]) if read_based else 1.0
            if not stored:
                stored = True
                factor /= read  # te_grid_read_throughput_effect takes it out once
            if command and command >= 10 and moved > 0:
                factor = min(2.0, max(0.2, moved / command / read))
            if month in idle:
                command = 0
                shares += [0.0] * len(weeks)
                continue
            command = flow / factor / read
            for t in weeks:
                moved = command * max(0.0, 1 + t) * staffing
                shares.append(moved / flow)
        return shares, factor

    WARM = -0.025 * 1.81

    def test_a_running_stations_order_is_unchanged_wherever_a_step_lands(self):
        # A -0.25 line (seabed overexploitation) lands in each week of month 2
        # in turn: the station moves what the build before moved, so the step
        # isn't counted twice the month after (1.355 of its flow in the first
        # build when it landed in the second week).
        for week in range(4):
            weekly = [[self.WARM] * 4 for _ in range(5)]
            for w in range(week, 4):
                weekly[2][w] = self.WARM - 0.25
            for m in (3, 4):
                weekly[m] = [self.WARM - 0.25] * 4
            for staffing in (1.0, 0.8):
                new, _ = self.model(weekly, staffing)
                old, _ = self.model(weekly, staffing, read_based=False)
                # From its first measure on (the first month, a new station's
                # first order, now moves its flow at today's throughput).
                for a, b in zip(new[4:], old[4:]):
                    self.assertAlmostEqual(a, b, msg=(week, staffing))
                for share in new[16:]:
                    self.assertAlmostEqual(share, 1.0, msg=(week, staffing))
            new, _ = self.model(weekly)
            self.assertAlmostEqual(new[0], 1.0)

    def test_the_factor_holds_staffing_alone(self):
        _, factor = self.model([[self.WARM] * 4] * 4, staffing=0.8)
        self.assertAlmostEqual(factor, 0.8)
        _, factor = self.model([[self.WARM] * 4] * 4, staffing=0.8, read_based=False)
        self.assertAlmostEqual(factor, 0.8 * (1 + self.WARM))

    def test_a_station_back_from_idle_moves_its_flow_at_todays_throughput(self):
        # Idle in months 1 and 2 while the -0.25 line lands: its kept factor
        # holds staffing alone, so it moves its flow the month it is back. The
        # build before kept a factor with the old throughput in it.
        weekly = [[self.WARM] * 4, [self.WARM] * 4] + [[self.WARM - 0.25] * 4] * 2
        new, _ = self.model(weekly, idle=(1, 2))
        old, _ = self.model(weekly, idle=(1, 2), read_based=False)
        self.assertAlmostEqual(new[12], 1.0)
        self.assertAlmostEqual(old[12], (1 + self.WARM - 0.25) / (1 + self.WARM))

    def test_a_save_from_before_keeps_its_factors_measure(self):
        # Its factor carries the warming line and no read is stored. Taken out
        # once, a factor measured at the first run and one kept through it both
        # move the station's flow.
        weekly = [[self.WARM] * 4] * 3
        for idle in ((), (0,)):
            shares, factor = self.model(weekly, factor=1 + self.WARM, stored=False, idle=idle)
            self.assertAlmostEqual(factor, 1.0, msg=idle)
            for share in shares:
                self.assertIn(round(share, 9), (0.0, 1.0), idle)

    def test_the_balancing_reads_the_throughput_before_the_factor(self):
        balance = _top_level(self.effects, "te_grid_balance_region_effect")
        order = [balance.index(s) for s in (
            "te_grid_read_throughput_effect = yes",
            "te_grid_power_rate_selfcheck_effect = yes",
            "te_grid_throughput_selfcheck_effect = yes",
            "name = te_grid_factor ",
            "te_grid_set_station_flow_effect = yes")]
        self.assertEqual(order, sorted(order))
        read = _top_level(self.effects, "te_grid_read_throughput_effect")
        self.assertIn("is_building_type = building_grid_transfer_station", read)
        self.assertIn("value = prev.modifier:building_throughput_add", read)
        # Stored before the factor reads it, on both branches.
        self.assertEqual(read.count("set_variable = { name = te_grid_throughput value = local_var:te_grid_throughput_now }"), 2)
        # A factor from before #1248 loses its throughput once, after the read is stored.
        first = _sub(read, "else")
        self.assertLess(first.index("name = te_grid_throughput value"),
                        first.index("change_variable = { name = te_grid_factor divide = te_grid_station_throughput_value }"))
        self.assertIn("change_local_variable = { name = te_grid_throughput_step subtract = 10 }", first)
        value = _top_level(self.values, "te_grid_station_throughput_value")
        self.assertIn("add = var:te_grid_throughput", value)
        self.assertIn("min = 0.2", value)
        self.assertEqual(_top_level(self.values, "te_grid_station_factor_value")
                         .count("divide = te_grid_station_throughput_value"), 2)
        for name in ("te_grid_command_value", "te_grid_import_command_value"):
            self.assertIn("divide = te_grid_station_throughput_value", _top_level(self.values, name), name)
        self.assertIn("remove_variable = te_grid_throughput", _top_level(self.effects, "te_grid_clear_state_effect"))

    def test_both_measuring_checks_wait_for_a_steady_read(self):
        # A step after the station's last tick puts last week's output off the read.
        for name in ("te_grid_power_rate_selfcheck_effect", "te_grid_throughput_selfcheck_effect"):
            check = _top_level(self.effects, name)
            lo = float(re.search(r"local_var:te_grid_throughput_step > (-[\d.]+)", check).group(1))
            hi = float(re.search(r"local_var:te_grid_throughput_step < ([\d.]+)", check).group(1))
            self.assertEqual(lo, -hi, name)
            self.assertLessEqual(hi, 0.01, name)
            # No earlier read: the step is -10 or less, outside.
            self.assertFalse(lo < -10 + self.WARM < hi, name)

    def test_the_self_check_tells_a_read_that_cuts_the_lines_from_one_that_does_not(self):
        check = _top_level(self.effects, "te_grid_throughput_selfcheck_effect")
        self.assertIn("TE_SELF_CHECK OK grid_throughput", check)
        self.assertIn("TE_SELF_CHECK BROKEN grid_throughput", check)
        self.assertIn("te_grid_station_staffed_throughout = yes", check)
        self.assertIn("var:te_grid_command >= 100", check)
        gate_lo = float(re.search(r"var:te_grid_throughput <= (-[\d.]+)", check).group(1))
        gate_hi = float(re.search(r"var:te_grid_throughput >= ([\d.]+)", check).group(1))
        self.assertEqual(gate_lo, -gate_hi)
        occupancy = float(re.search(r"occupancy >= ([\d.]+)", check).group(1))
        factor_gate = float(re.search(r"var:te_grid_factor >= ([\d.]+)", check).group(1))
        ok_lo = float(re.search(r"global_var:te_grid_chk_throughput_share >= ([\d.]+)", check).group(1))
        ok_hi = float(re.search(r"global_var:te_grid_chk_throughput_share <= ([\d.]+)", check).group(1))
        share = _top_level(self.values, "te_grid_chk_throughput_share_value")
        self.assertIn("divide = te_grid_station_throughput_value", share)
        self.assertIn("divide = global_var:te_grid_chk_occupancy", share)
        # Read right, the share is last week's staffing over today's occupancy.
        # Full at the last measure (the factor gate) and now (the occupancy
        # gate), last week's staffing lies between the two gates and 1.
        for last_week in (min(occupancy, factor_gate), 1.0):
            for now in (occupancy, 1.0):
                self.assertTrue(ok_lo <= last_week / now <= ok_hi, (last_week, now))
        # Lines that don't feel the read: 1 / (1 + t), at the gate and past it.
        for t in (gate_lo, gate_hi, -0.1, -0.3):
            self.assertFalse(ok_lo <= 1 / (1 + t) <= ok_hi, t)


class ConnectionTest(unittest.TestCase):
    """The Power Grid Connection: the station's method gives its state the
    connection, so its tooltip says the station joins the state to a grid, and
    the balancing reads the same line to decide which stations take part."""

    def test_connection_is_a_script_only_state_boolean(self):
        body = _code(_top_level(_read(TYPES), "state_power_grid_connection_bool"))
        self.assertRegex(body, r"\bboolean = yes\b")
        self.assertRegex(body, r"\bscript_only = yes\b")
        self.assertRegex(body, r"\bcolor = good\b")

    def test_a_disruption_is_its_own_boolean_and_cuts_the_connection(self):
        # A boolean only takes yes, so an outage can't take the connection away: it grants its own line.
        body = _code(_top_level(_read(TYPES), "state_power_grid_disrupted_bool"))
        self.assertRegex(body, r"\bboolean = yes\b")
        self.assertRegex(body, r"\bscript_only = yes\b")
        self.assertRegex(body, r"\bcolor = bad\b")
        connected = _top_level(_code(_read(TRIGGERS)), "te_grid_state_connected")
        self.assertIn("modifier:state_power_grid_disrupted_bool = no", connected)

    def test_the_method_grants_it_unscaled_on_the_state(self):
        # Unscaled, so an empty station keeps its connection as it keeps its order.
        method = _code(_top_level(_read(PMS), "pm_grid_transfer_base"))
        state = _sub(method, "state_modifiers")
        self.assertRegex(_sub(state, "unscaled"), r"\bstate_power_grid_connection_bool = yes\b")
        self.assertNotRegex(_sub(method, "building_modifiers"), r"\bstate_power_grid_connection_bool\b")

    def test_a_station_is_online_when_its_state_is_connected(self):
        triggers = _code(_read(TRIGGERS))
        connected = _top_level(triggers, "te_grid_state_connected")
        self.assertIn("modifier:state_power_grid_connection_bool = yes", connected)
        online = _top_level(triggers, "te_grid_station_online")
        self.assertIn("te_grid_state_connected = yes", online)
        # The station still moves the power, so it must be built as well.
        self.assertIn("is_building_type = building_grid_transfer_station", online)
        self.assertIn("level >= 1", online)

    def test_its_name_links_the_concept(self):
        loc = {}
        for name in os.listdir(LOC_DIR):
            if name.endswith(".yml"):
                loc.update(re.findall(r'(?m)^ ([\w.]+):\d* "(.*)"\s*$', _read(os.path.join(LOC_DIR, name))))
        self.assertIn("[concept_power_grid]", loc["state_power_grid_connection_bool"])
        self.assertIn("[concept_power_grid]", loc["state_power_grid_connection_bool_desc"])
        self.assertIn("[concept_power_grid]", loc["state_power_grid_disrupted_bool"])

    def test_self_checks_read_the_connection_before_the_run_uses_it(self):
        world = _code(_top_level(_read(EFFECTS), "te_grid_world_update_effect"))
        self.assertLess(world.index("te_grid_connection_selfcheck_effect = yes"),
                        world.index("limit = { te_grid_station_online = yes }"))
        check = _code(_top_level(_read(EFFECTS), "te_grid_connection_selfcheck_effect"))
        for name in ("grid_connection ", "grid_connection_unstaffed "):
            self.assertIn(f"TE_SELF_CHECK OK {name}", check)
            self.assertIn(f"TE_SELF_CHECK BROKEN {name}", check)
        # They judge the connection's own line, at states with no disruption, which would cut it.
        self.assertNotIn("te_grid_state_connected", check)
        self.assertEqual(check.count("limit = { modifier:state_power_grid_connection_bool = yes }"), 2)
        self.assertEqual(check.count("modifier:state_power_grid_disrupted_bool = no"), 2)
        # Judged at a station already built at the last run, so its modifiers have settled,
        # and the empty one at a station with no staff then and now.
        self.assertLess(check.index("has_variable = te_grid_chk_station_seen"), check.index("TE_SELF_CHECK OK"))
        self.assertIn("set_variable = { name = te_grid_chk_station_seen value = yes days = 45 }", check)
        unstaffed = check[check.index("te_grid_connection_unstaffed_checked }"):]
        self.assertLess(unstaffed.index("has_variable = te_grid_chk_unstaffed"),
                        unstaffed.index("TE_SELF_CHECK OK grid_connection_unstaffed"))
        self.assertIn("set_variable = { name = te_grid_chk_unstaffed value = yes days = 45 }", check)


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
                    "pm_grid_hvdc_interconnector", "pm_grid_hvdc_interconnector_desc",
                    "building_grid_hvdc_interconnector", "building_grid_hvdc_interconnector_desc",
                    "te_grid_hvdc_needs_station_tt", "state_building_grid_hvdc_interconnector_max_level_add",
                    "grid_interconnection_agreement", "grid_interconnection_agreement_desc",
                    "grid_interconnection_agreement_effects_desc", "grid_interconnection_agreement_article_short_desc",
                    "treaty_name_grid_interconnection_treaty", "treaty_name_country_adj_country_adj_power_pool",
                    "TE_STATE_GRID_STATUS", "TE_STATE_GRID_TT", "AI_GRID_STATIONS_MEET",
                    "TE_STATE_GRID_ROW_MARKET", "TE_STATE_GRID_ROW_MARKET_TT", "TE_STATE_GRID_ROW_PASS",
                    "TE_STATE_GRID_ROW_PASS_TT", "te_grid_market_exports", "te_grid_market_imports",
                    "te_grid_market_send_more", "te_grid_market_receive_more",
                    "building_grid_undersea_cable_range_add", "building_grid_undersea_cable_range_add_desc",
                    "TE_STATE_GRID_ROW_CABLES", "TE_STATE_GRID_ROW_CABLES_TT", "te_grid_cable_link_line",
                    "te_grid_cables_intro", "te_grid_cables_none",
                    "state_power_grid_connection_bool", "state_power_grid_connection_bool_desc",
                    "state_power_grid_disrupted_bool", "state_power_grid_disrupted_bool_desc"):
            self.assertIn(key, keys)


if __name__ == "__main__":
    unittest.main()
