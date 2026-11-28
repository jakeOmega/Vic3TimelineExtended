"""The Resort Colony as a building of its own (issue #1948).

Design: docs/superpowers/specs/2026-11-21-resort-colony-building-design.md.
The Resort Colony method left the Extraplanetary Base for building_space_resort,
whose levels work their own room at each world (the RESORTS table in
gen_solar_sites.py, plus 20 a staffed Off-World Resort level, plus 20 in Earth
orbit; 10 each until #2141) best draw first, -75% past it: the twin of base room.

Run: python3 -m pytest test_resort_colony.py -q
"""
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import gen_solar_sites as gss  # noqa: E402
from test_solar_sites import _block, _raw, _strip  # noqa: E402

# The owner-reviewed draws (design § 6.2), in percent.
DRAWS = {
    "tranquility": 30,
    "olympus_mons": 25, "valles_marineris": 25,
    "shackleton": 15, "marius_hills": 15, "venus": 15, "iapetus": 15, "enceladus": 15,
    "imbrium": 10, "peary": 10, "vesta": 10, "callisto": 10, "titan": 10,
    "hellas_planitia": 5, "ceres": 5, "rhea": 5, "mimas": 5,
    "daedalus": 0, "utopia_planitia": 0, "arcadia_planitia": 0, "psyche": 0, "europa": 0, "ganymede": 0,
    "miranda": 0,
    "mercury": -5, "pallas": -5, "io": -5, "amalthea": -5, "triton": -5,
    "hygiea": -10, "pluto": -10,
    "himalia": -15, "titania": -15, "oberon": -15, "ariel": -15,
    "proteus": -25, "haumea": -25,
    "eris": -30, "makemake": -30,
    "sedna": -35,
}


def _values():
    return _strip(_raw(*gss.VALUES_OUT.parts))


def _effects():
    return _strip(_raw(*gss.EFFECTS_OUT.parts))


class ResortTableTest(unittest.TestCase):
    def test_every_site_has_a_resort_row(self):
        self.assertEqual(set(gss.RESORTS), {s.key for s in gss.SITES})

    def test_room_is_twice_the_worlds_room_for_now(self):
        # The design's starting value (§ 6.1): a world that houses more people
        # houses more guests; doubled on 2026-11-28 (the owner: double the resort
        # room from every source). A later tune of one world changes this test on purpose.
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertEqual(site.resort_room, 2 * site.room)
        self.assertEqual(sum(s.resort_room for s in gss.SITES), 1890)

    def test_draws_are_the_designs(self):
        self.assertEqual({s.key: s.resort_draw for s in gss.SITES}, DRAWS)
        for draw in DRAWS.values():
            self.assertEqual(draw % 5, 0)
            self.assertTrue(-35 <= draw <= 30)

    def test_constants(self):
        self.assertEqual(gss.ORBIT_RESORT_ROOM, 20)
        self.assertEqual(gss.RESORT_TECH, "space_colonization")
        self.assertEqual(gss.RESORT_OVERFLOW_DRAW, -75)

    def test_tiers_best_draw_first(self):
        tiers = gss.resort_tiers()
        self.assertEqual(tiers[0].key, "tranquility")
        self.assertEqual(tiers[-1].key, "sedna")
        self.assertEqual(tiers.count(None), 1)
        orbit = tiers.index(None)
        for i, tier in enumerate(tiers):
            if tier is None:
                continue
            with self.subTest(site=tier.key):
                if tier.resort_draw > 0:
                    self.assertLess(i, orbit)
                else:
                    self.assertGreater(i, orbit)
        draws = [0 if t is None else t.resort_draw for t in tiers]
        self.assertEqual(draws, sorted(draws, reverse=True))


class ResortRoomTest(unittest.TestCase):
    def test_room_total(self):
        room = _block(_values(), "sr_resort_room_total")
        self.assertIn("value = 0", room)
        self.assertIn("if = { limit = { has_technology_researched = space_colonization } add = 20 }", room)
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"{gss.site_serves(site)} }} add = sr_site_resort_room_{site.key} }}", room)

    def test_site_room(self):
        values = _values()
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                world = _block(values, f"sr_site_resort_room_{k}")
                self.assertIn(f"value = {site.resort_room}", world)
                # Doubled where a discovery there boosts the Off-World Resort (2026-11-25).
                self.assertIn(f"add = {{ value = {gss.eff_value(site, 'resort')} multiply = sr_mod_resort_room "
                              "floor = yes }", world)

    def test_fill_and_next_fill(self):
        effects = _effects()
        fill = _block(effects, "sr_resort_fill")
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertEqual(fill.count(f"max = sr_site_resort_room_{site.key} "), 1)
        self.assertEqual(fill.count("max = 20 "), 1)
        self.assertIn("multiply = -75 add = local_var:sr_rs_sum", fill)
        # A colony's levels x its draw, with its Cultural Centers' points (the owner,
        # 2026-11-24), join the sum, a table draw of 0 too; Earth orbit's 0 adds nothing.
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertEqual(fill.count(f"multiply = sr_site_resort_draw_{site.key} add = local_var:sr_rs_sum"), 1)
        self.assertEqual(fill.count("add = local_var:sr_rs_sum"), len(gss.SITES) + 1)  # and the overflow
        nxt = _block(effects, "sr_resort_next_fill")
        self.assertIn("value = sr_resort_queued_levels", nxt)
        self.assertIn("set_variable = { name = sr_resort_next_draw value = -75 }", nxt)
        self.assertIn("set_variable = { name = sr_resort_next_draw value = 0 }", nxt)
        for site in gss.SITES:
            self.assertIn(f"set_variable = {{ name = sr_resort_next_draw value = sr_site_resort_draw_{site.key} }}", nxt)

    def test_cultural_centers_add_to_the_draw(self):
        """The owner, 2026-11-24: a Cultural Center adds 1% (a point) to its
        world's Resort Draw, a staffed level at a time."""
        values = _strip(_raw(*gss.VALUES_OUT.parts))
        hand = _strip(_raw("common", "script_values", "sr_colony_module_values.txt"))
        self.assertRegex(hand, r"(?m)^sr_mod_culture_draw = \{ value = 1 \}")
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                draw = _block(values, f"sr_site_resort_draw_{k}")
                self.assertIn(f"value = {site.resort_draw}\n", draw)
                self.assertIn(f"add = {{ value = {gss.eff_value(site, 'culture')} multiply = sr_mod_culture_draw }}", draw)
        loc = _raw("localization", "english", "te_journal_entries_l_english.yml")
        tip = re.search(r'^ je_space_race_widget_mod_culture_tt:0 "(.*)"$', loc, re.M).group(1)
        self.assertIn("#v +1#! point of [concept_sr_resort_draw]", tip)

    def test_hand_values(self):
        values = _strip(_raw("common", "script_values", "sr_colony_module_values.txt"))
        self.assertRegex(values, r"(?m)^sr_mod_resort_room = \{ value = 20 \}")
        # Each state's colony by the engine's b: lookup, never a walk of its buildings: the private
        # investment pass reads the queued count in every state.
        levels = _block(_values(), "sr_resort_levels")  # gss.render_room_levels (#1951)
        self.assertIn("limit = { exists = b:building_space_resort }", levels)
        self.assertIn("add = b:building_space_resort.level\n", levels)
        queued = _block(_values(), "sr_resort_queued_levels")
        self.assertIn("limit = { exists = b:building_space_resort }", queued)
        self.assertIn("add = b:building_space_resort.level_after_queued_constructions", queued)
        for block in (levels, queued):
            self.assertNotIn("scope_building", block)

    def test_display(self):
        display = _strip(_raw(*gss.DISPLAY_OUT.parts))
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"sr_disp_site_resort_room_{site.key} = {{ value = sr_site_resort_room_{site.key} }}",
                              display)
                self.assertIn(f"sr_disp_site_resort_draw_{site.key} = {{ value = sr_site_resort_draw_{site.key} }}",
                              display)


def _goods():
    """{good: (base price, local)} from vanilla_parsed and the mod's goods files,
    prices as pm_costs.py reads them."""
    import json
    import pm_costs
    prices = pm_costs.load_goods()
    local = set()
    with open(os.path.join(REPO, "vanilla_parsed", "common", "goods.json"), encoding="utf-8") as f:
        for key, value in json.load(f).items():
            if value[1].get("local", [None, None])[1] == "yes":
                local.add(key)
    goods_dir = os.path.join(REPO, "common", "goods")
    for name in os.listdir(goods_dir):
        text = _strip(_raw("common", "goods", name))
        for m in re.finditer(r"(?m)^(?:\w+:)?(\w+)\s*=\s*\{", text):
            if re.search(r"\blocal\s*=\s*yes", _block(text, m.group(0).split("=")[0].strip())):
                local.add(m.group(1))
    return {good: (price, good in local) for good, price in prices.items()}


class ResortBuildingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.buildings = _strip(_raw("common", "buildings", "extra_buildings.txt"))
        cls.groups = _strip(_raw("common", "production_method_groups", "extra_pm_groups.txt"))
        cls.pms = _strip(_raw("common", "production_methods", "extra_pms.txt"))

    def test_building_shape(self):
        resort = _block(self.buildings, "REPLACE_OR_CREATE:building_space_resort")
        self.assertIn("building_group = bg_exotic", resort)
        self.assertIn("space_colonization", _block(resort, "unlocking_technologies"))
        groups = _block(resort, "production_method_groups").split()
        self.assertEqual(groups, ["pmg_base_building_space_resort", "pmg_launch_to_orbit_building_space_mine",
                                  "pmg_transport_in_space_building_space_mine", "pmg_maintenance_intensive"])
        self.assertIn("required_construction = construction_cost_space_mine", resort)
        self.assertIn("ownership_type = self", resort)
        self.assertIn("owner ?= { sr_resort_may_build_government = yes }", _block(resort, "can_build_government"))
        self.assertIn("owner ?= { sr_resort_may_build_private = yes }", _block(resort, "can_build_private"))

    def test_base_group_is_the_four_mining_methods(self):
        base = _block(self.groups, "REPLACE_OR_CREATE:pmg_base_building_space_mine")
        self.assertEqual(_block(base, "production_methods").split(),
                         ["pm_regolith_processing", "pm_space_mine", "pm_space_colony_mining",
                          "pm_self_replicating_miners"])
        resort = _block(self.groups, "REPLACE_OR_CREATE:pmg_base_building_space_resort")
        self.assertEqual(_block(resort, "production_methods").split(), ["pm_space_colony_vacation"])

    def test_method_figures(self):
        goods = _goods()
        body = _block(_block(self.pms, "pm_space_colony_vacation"), "workforce_scaled")
        inputs = {g: float(n) for g, n in re.findall(r"goods_input_(\w+)_add = ([\d.]+)", body)}
        outputs = {g: float(n) for g, n in re.findall(r"goods_output_(\w+)_add = ([\d.]+)", body)}
        self.assertEqual(inputs, {"electronic_components": 15, "radios": 30, "digital_access": 10,
                                  "advanced_materials": 0.5, "launch_capacity": 480, "wine": 50,
                                  "luxury_furniture": 30, "fruit": 30})
        # Tourism doubled, 900 to 1,800, on 2026-11-25 (the owner: "underpowered").
        self.assertEqual(outputs, {"fine_art": 300, "tourism": 1800})
        cost = sum(n * goods[g][0] for g, n in inputs.items())
        value = sum(n * goods[g][0] for g, n in outputs.items())
        self.assertEqual((cost, value, value - cost), (108000, 240000, 132000))
        # Call 4: no services (a local good), and no local good added; Digital
        # Access, local, stays as the required input.
        self.assertNotIn("services", inputs)
        self.assertEqual([g for g in inputs if goods[g][1]], ["digital_access"])
        self.assertIn("required_input_goods = digital_access", _block(self.pms, "pm_space_colony_vacation"))
        self.assertEqual(inputs["advanced_materials"], 2.5 / 5)

    def test_axiom_lists_the_resort(self):
        companies = _strip(_raw("common", "company_types", "extra_companies_flavored.txt"))
        types = _block(_block(companies, "company_axiom_space"), "building_types").split()
        self.assertIn("building_space_resort", types)
        self.assertIn("building_space_mine", types)

    def test_lists_name_the_resort(self):
        misc = _strip(_raw("common", "scripted_triggers", "misc_triggers.txt"))
        self.assertIn("is_building_type = building_space_resort", _block(misc, "is_privately_expandable_building_type"))
        debris = _strip(_raw("common", "scripted_triggers", "te_orbital_debris_triggers.txt"))
        self.assertIn("is_building_type = building_space_resort", _block(debris, "te_debris_uses_orbit"))

    def test_loc(self):
        buildings = _raw("localization", "english", "te_buildings_l_english.yml")
        self.assertIn(' building_space_resort:0 "Resort Colony"', buildings)
        methods = _raw("localization", "english", "te_production_methods_l_english.yml")
        self.assertIn(' pm_space_colony_vacation:0 "Luxury Resorts"', methods)
        self.assertIn(" pmg_base_building_space_resort:0 ", methods)


class ResortRefreshTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw("common", "scripted_effects", "sr_colony_module_effects.txt"))
        cls.triggers = _strip(_raw(*gss.TRIGGERS_OUT.parts))  # gss.render_room_gates (#1951)
        cls.modifiers = _strip(_raw("common", "static_modifiers", "space_race_modifiers.txt"))

    def test_refresh_removes_first_and_averages(self):
        refresh = _block(self.effects, "sr_resort_refresh")
        adds = refresh.index("add_modifier")
        for name in ("sr_resort_room_bonus", "sr_resort_room_penalty"):
            self.assertLess(refresh.index(f"remove_modifier = {name}"), adds)
            # Removed before the rule's test, so Races Only mid-game drops them (Review Focus 3).
            self.assertLess(refresh.index(f"remove_modifier = {name}"),
                            refresh.index("sr_colonies_contested_enabled = yes"))
        self.assertIn("sr_resort_fill = yes", refresh)
        self.assertIn("sr_resort_next_fill = yes", refresh)
        self.assertRegex(refresh, r"value = local_var:sr_rs_sum\s+divide = local_var:sr_rs_levels")
        self.assertIn("set_local_variable = { name = sr_rs_levels value = sr_resort_levels }", refresh)
        self.assertIn("add_modifier = { name = sr_resort_room_bonus multiplier = var:sr_resort_units }", refresh)
        self.assertIn("add_modifier = { name = sr_resort_room_penalty multiplier = var:sr_resort_units }", refresh)

    def test_modifier_pair(self):
        self.assertIn("building_space_resort_throughput_add = 0.01", _block(self.modifiers, "sr_resort_room_bonus"))
        self.assertIn("building_space_resort_throughput_add = -0.01", _block(self.modifiers, "sr_resort_room_penalty"))
        types = _strip(_raw("common", "modifier_type_definitions", "mod_entity_modifier_types.txt"))
        self.assertIn("percent = yes", _block(types, "building_space_resort_throughput_add"))
        loc = _raw("localization", "english", "te_buildings_l_english.yml")
        self.assertIn(' building_space_resort_throughput_add:0 "$building_space_resort$ [concept_throughput]"', loc)

    def test_gates(self):
        room = _block(self.triggers, "sr_resort_has_room")
        self.assertIn("NOT = { sr_colonies_contested_enabled = yes }", room)
        self.assertIn("sr_resort_queued_levels < sr_resort_room_total", room)
        self.assertIn("is_ai = no", _block(self.triggers, "sr_resort_may_build_government"))
        self.assertIn("sr_resort_has_room = yes", _block(self.triggers, "sr_resort_may_build_government"))
        private = _block(self.triggers, "sr_resort_may_build_private")
        self.assertNotIn("is_ai", private)
        self.assertIn("sr_resort_has_room = yes", private)
        self.assertIn("text = sr_resort_room_full_tt", private)

    def test_monthly_and_hook(self):
        monthly = _strip(_raw("common", "on_actions", "space_race_on_actions.txt"))
        self.assertRegex(monthly, r"limit = \{ has_technology_researched = space_colonization \}\s+sr_resort_refresh = yes")
        hooks = _strip(_raw("common", "on_actions", "extra_on_actions.txt"))
        for name in ("te_on_building_built", "te_on_building_expanded"):
            with self.subTest(on_action=name):
                self.assertRegex(_block(hooks, name), r"is_building_type = building_space_resort\s+exists = owner\s+\}"
                                                      r"\s+owner = \{ sr_resort_hook_fire = yes \}")
        fire = _block(_effects(), "sr_resort_hook_fire")  # gss.render_room_hook (#1951)
        self.assertIn("NOT = { has_variable = sr_resort_hook_pending }", fire)
        self.assertIn("set_variable = { name = sr_resort_hook_pending value = yes days = 2 }", fire)
        self.assertIn("trigger_event = { id = space_race_events.112 days = 1 }", fire)
        events = _raw("events", "space_race_events.txt")
        event = _block(_strip(events), "space_race_events.112")
        self.assertIn("hidden = yes", event)
        self.assertIn("has_technology_researched = space_colonization", _block(event, "trigger"))
        self.assertIn("remove_variable = sr_resort_hook_pending", event)
        self.assertIn("sr_resort_refresh = yes", event)
        self.assertRegex(events, r"space_race_events\.112 = \{[^}]*# REVIEWED 2026-11-21 \(delayed_trigger\)")

    def test_carry_over_lines(self):
        debris = _strip(_raw("common", "static_modifiers", "te_orbital_debris_modifiers.txt"))
        pms = _strip(_raw("common", "production_methods", "extra_pms.txt"))
        for name, body in (("sr_commercial_space_dividend", _block(self.modifiers, "sr_commercial_space_dividend")),
                           ("te_orbital_debris", _block(debris, "te_orbital_debris")),
                           ("pm_spaceport", _block(_block(pms, "pm_spaceport"), "state_modifiers"))):
            with self.subTest(modifier=name):
                mine = re.search(r"building_space_mine_throughput_add = (-?[\d.]+)", body).group(1)
                resort = re.search(r"building_space_resort_throughput_add = (-?[\d.]+)", body).group(1)
                self.assertEqual(float(mine), float(resort))

    def test_no_mining_bonus_reaches_the_resort(self):
        for path in (("common", "static_modifiers", "space_race_modifiers.txt"),
                     ("common", "static_modifiers", "space_race_discovery_modifiers.txt")):
            text = _strip(_raw(*path))
            for m in re.finditer(r"(?m)^(\w+) = \{", text):
                name = m.group(1)
                if (name.startswith(("sr_colony_", "sr_discovery_"))
                        or name in ("sr_mars_robotic_precursor", "sr_extraplanetary_commercial")):
                    with self.subTest(modifier=name):
                        self.assertNotIn("building_space_resort_throughput_add", _block(text, name))

    def test_nation_tab_lists_the_pair(self):
        import gen_nation_tab
        self.assertIn("sr_resort_room_*", str(gen_nation_tab.SECTIONS["science_and_space"]))


def _top_block(text, name):
    """A top-level definition's body: `name = {` at the start of a line, not a call to it."""
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    if not m:
        raise AssertionError(f"no definition {name}")
    return _block(text[m.start():], name)


class ResortStateCancelTest(unittest.TestCase):
    """The Resort Colony free of its state (#1953; the scope
    docs/superpowers/specs/2026-11-22-colony-people-and-off-world-tourism-scope.md § 2):
    the state's share of its Tourism and Fine Art output multipliers, the state's
    read less its owner's, taken back off the building each month."""

    GOODS = ("tourism", "fine_art")

    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw("common", "scripted_effects", "sr_colony_module_effects.txt"))
        cls.modifiers = _strip(_raw("common", "static_modifiers", "space_race_modifiers.txt"))
        cls.refresh = _top_block(cls.effects, "sr_resort_state_refresh")
        cls.good = _top_block(cls.effects, "sr_resort_state_good")
        cls.check = _top_block(cls.effects, "sr_resort_state_self_check")

    def test_unit_pairs(self):
        for good in self.GOODS:
            for side, value in (("bonus", "0.01"), ("penalty", "-0.01")):
                with self.subTest(good=good, side=side):
                    body = _block(self.modifiers, f"sr_resort_state_{good}_{side}")
                    self.assertRegex(body, rf"(?m)^\s*goods_output_{good}_mult = {re.escape(value)}\s*$")
                    # Only the good's output: no throughput, no other good.
                    self.assertEqual(len(re.findall(r"(?m)^\s*\w+_(?:mult|add) = ", body)), 1)

    def test_share_is_the_state_read_less_the_owners(self):
        self.assertRegex(self.good, r"name = sr_resort_state_\$GOOD\$\s+value = \{\s+"
                                    r"value = modifier:goods_output_\$GOOD\$_mult\s+"
                                    r"subtract = owner\.modifier:goods_output_\$GOOD\$_mult\s+"
                                    r"multiply = 100\s+\}")

    def test_removed_before_added_and_signed(self):
        building = _block(self.good, "b:building_space_resort")
        first_add = building.index("add_modifier")
        for side in ("bonus", "penalty"):
            self.assertLess(building.index(f"remove_modifier = sr_resort_state_$GOOD$_{side}"), first_add)
        # A share above 0 (the state lifts the good) takes the penalty; below 0, the bonus.
        self.assertRegex(building, r"root\.var:sr_resort_state_\$GOOD\$ > 0 \}\s+add_modifier = \{ name = "
                                   r"sr_resort_state_\$GOOD\$_penalty multiplier = root\.var:sr_resort_state_\$GOOD\$_units \}")
        self.assertRegex(building, r"root\.var:sr_resort_state_\$GOOD\$ < 0 \}\s+add_modifier = \{ name = "
                                   r"sr_resort_state_\$GOOD\$_bonus multiplier = root\.var:sr_resort_state_\$GOOD\$_units \}")
        # The size is the share's absolute value.
        self.assertIn("set_variable = { name = sr_resort_state_$GOOD$_units value = var:sr_resort_state_$GOOD$ }", self.good)
        self.assertRegex(self.good, r"value = var:sr_resort_state_\$GOOD\$\s+multiply = -1")

    def test_refresh_covers_both_goods_after_the_check(self):
        calls = [m.group(1) for m in re.finditer(r"sr_resort_state_good = \{ GOOD = (\w+) \}", self.refresh)]
        self.assertEqual(calls, list(self.GOODS))
        self.assertLess(self.refresh.index("sr_resort_state_self_check = yes"),
                        self.refresh.index("sr_resort_state_good = {"))
        self.assertIn("has_building = building_space_resort", self.refresh)
        # Whatever the game rule: the hotels are off-world under Races Only too.
        self.assertNotIn("sr_colonies_contested_enabled", self.refresh)
        # A state that lost its building drops its figures.
        for var in ("sr_resort_state_tourism", "sr_resort_state_tourism_units",
                    "sr_resort_state_fine_art", "sr_resort_state_fine_art_units"):
            self.assertIn(f"remove_variable = {var}\n", self.refresh)

    def test_one_refresh_site_on_the_monthly_state_pulse(self):
        hooks = _strip(_raw("common", "on_actions", "extra_on_actions.txt"))
        pulse = _block(_block(hooks, "on_monthly_pulse_state"), "on_actions").split()
        self.assertEqual(pulse[0], "sr_resort_state_on_action")
        self.assertLess(pulse.index("sr_resort_state_on_action"), pulse.index("tourism_on_action"))
        self.assertIn("sr_resort_state_refresh = yes", _block(hooks, "sr_resort_state_on_action"))
        callers, adders = [], []
        for top in ("common", "events"):
            for dirpath, _dirs, files in os.walk(os.path.join(REPO, top)):
                for name in files:
                    if not name.endswith(".txt"):
                        continue
                    rel = os.path.relpath(os.path.join(dirpath, name), REPO)
                    text = _strip(_raw(rel))
                    callers += [rel] * len(re.findall(r"\bsr_resort_state_refresh = yes", text))
                    adders += [rel] * len(re.findall(r"name = sr_resort_state_[\w$]+_(?:bonus|penalty)", text))
        self.assertEqual(callers, ["common/on_actions/extra_on_actions.txt"])
        self.assertEqual(adders, ["common/scripted_effects/sr_colony_module_effects.txt"] * 2)

    def test_self_check(self):
        limit = _block(self.check, "limit")
        self.assertIn("NOT = { has_global_variable = sr_resort_state_checked }", limit)
        # Armed only where no failure can land in the band: a share of 40% or more on a building
        # that carries its cancel, a country line of 30% or more, and a share that has held.
        self.assertIn("var:sr_resort_state_tourism_units >= 40", limit)
        self.assertIn("has_modifier = sr_resort_state_tourism_bonus", limit)
        self.assertIn("has_modifier = sr_resort_state_tourism_penalty", limit)
        self.assertRegex(limit, r"owner = \{\s+OR = \{\s+modifier:goods_output_tourism_mult >= 0\.3\s+"
                                r"modifier:goods_output_tourism_mult <= -0\.3\s+\}")
        self.assertRegex(self.check, r"name = sr_rsc_drift\s+value = \{\s+value = modifier:goods_output_tourism_mult\s+"
                                     r"subtract = owner\.modifier:goods_output_tourism_mult\s+multiply = 100\s+"
                                     r"subtract = var:sr_resort_state_tourism\s+\}")
        drift = self.check.index("local_var:sr_rsc_drift <= 5")
        self.assertIn("local_var:sr_rsc_drift >= -5", self.check)
        # The once-a-game flag is set only once a verdict is reached.
        self.assertLess(drift, self.check.index("set_global_variable = { name = sr_resort_state_checked value = yes }"))
        self.assertIn("set_variable = { name = sr_rsc_check_building value = prev.modifier:goods_output_tourism_mult }",
                      self.check)
        self.assertRegex(self.check, r"value = var:sr_rsc_check_building\s+subtract = var:sr_rsc_check_state\s+"
                                     r"add = \{\s+value = var:sr_resort_state_tourism\s+divide = 100\s+\}")
        self.assertIn("var:sr_rsc_check_own >= -0.05", self.check)
        self.assertIn("var:sr_rsc_check_own <= 0.25", self.check)
        self.assertIn('debug_log = "TE_SELF_CHECK OK resort_state ', self.check)
        self.assertIn('debug_log = "TE_SELF_CHECK BROKEN resort_state ', self.check)

    def test_self_check_failures_miss_the_band(self):
        """Each failure the check names lands 0.3 or more outside -0.05..+0.25 at the arming floors
        (share 40 points, a country line of 0.3, 5 points of drift), whatever the building's own line."""
        lo, hi = -0.05, 0.25
        for own in (0.0, 0.2):
            for share in (0.40, -0.40):
                for drift in (-0.05, 0.05):
                    now = share + drift
                    for country in (0.3, -0.3):
                        readings = {
                            # the cancel never reached the building
                            "missing cancel": own + share,
                            # the state's read leaves the country's lines out
                            "state without country": country + own,
                            # the building's read leaves the state's lines out
                            "building without state": own - now,
                        }
                        for name, reading in readings.items():
                            with self.subTest(failure=name, own=own, share=share, drift=drift, country=country):
                                self.assertFalse(lo <= reading <= hi, reading)
                    # and the working case reads the building's own line, whatever the drift
                    self.assertTrue(lo <= own <= hi)

    def test_loc(self):
        names = _raw("localization", "english", "te_miscellaneous_l_english.yml")
        descs = _raw("localization", "english", "te_concepts_l_english.yml")
        for good in self.GOODS:
            for side in ("bonus", "penalty"):
                key = f"sr_resort_state_{good}_{side}"
                with self.subTest(key=key):
                    self.assertIn(f' {key}:0 "Off-World Hotels"', names)
                    self.assertRegex(descs, rf'(?m)^ {key}_desc:0 "Our \$building_space_resort\$ hotels are off-world')
        draw = re.search(r'^ concept_sr_resort_draw_desc:0 "(.*)"$', descs, re.M).group(1)
        self.assertIn("The $tourism$ and $fine_art$ bonuses and penalties of the Earth state", draw)
        self.assertIn("$pm_spaceport$ level there gives it #v +1%#! throughput", draw)

    def test_nation_tab_places_the_pair_on_the_building(self):
        import gen_nation_tab
        self.assertEqual(gen_nation_tab.NOT_ON_COUNTRY["sr_resort_state_*"], "a Resort Colony building")

    def test_guide_and_play_test(self):
        space = _read("docs/player_guide/16-space.md")
        section = space[space.index("### Resort Colony room"):space.index("### Who holds a colony")]
        self.assertIn("Off-World Hotels", section)
        self.assertIn("+1% throughput", section)
        playtest = _read("docs/testing/solar-colonies-playtest.md")
        self.assertIn("`TE_SELF_CHECK OK/BROKEN resort_state ", playtest)
        self.assertIn("**A polluted state.**", playtest)


class ResortModuleTest(unittest.TestCase):
    def test_facility_is_a_hook(self):
        resort = gss.FACILITY["resort"]
        self.assertFalse(resort.modifier)
        self.assertTrue(resort.ships)
        self.assertEqual(gss.MODULE_CODES["resort"], 10)
        self.assertNotIn("sr_module_resort", _raw(*gss.ENTRY_OUT.parts))
        modifiers = _strip(_raw("common", "static_modifiers", "space_race_modifiers.txt"))
        self.assertNotRegex(modifiers, r"(?m)^sr_module_resort\s*=")

    def test_queue_needs_the_technology(self):
        triggers = _strip(_raw(*gss.TRIGGERS_OUT.parts))
        for site in gss.SITES:
            for t in gss.generic_types(site):
                with self.subTest(site=site.key, type=t):
                    body = _block(triggers, f"sr_mod_can_queue_{t}_{site.key}")
                    if t == "resort":
                        self.assertIn("has_technology_researched = space_colonization", body)
                    else:
                        self.assertNotIn("space_colonization", body)

    def test_reason_line(self):
        sguis = _strip(_raw("common", "scripted_guis", "sr_colony_sguis.txt"))
        self.assertRegex(sguis, r"limit = \{ scope:op = 10 \}\s+custom_tooltip = \{\s+text = sr_mod_req_resort_tech_tt"
                                r"\s+has_technology_researched = space_colonization")
        loc = _raw("localization", "english", "te_miscellaneous_l_english.yml")
        self.assertIn(" sr_mod_req_resort_tech_tt:0 ", loc)

    def test_ai_plans_a_resort_when_room_is_full(self):
        effects = _strip(_raw(*gss.EFFECTS_OUT.parts))
        for site in gss.SITES:
            with self.subTest(site=site.key):
                plan = _block(effects, f"sr_mod_ai_plan_{site.key}")
                resort = plan.index(f"sr_mod_can_queue_resort_{site.key} = yes")
                self.assertLess(plan.index(f"sr_mod_can_queue_mine_{site.key} = yes"), resort)
                branch = plan[resort:plan.index("}", plan.index("sr_resort_queued_levels", resort))]
                self.assertIn("sr_resort_queued_levels >= sr_resort_room_total", branch)

    def test_no_three_percent_text(self):
        for path, key in ((("localization", "english", "te_journal_entries_l_english.yml"),
                           "je_space_race_widget_mod_resort_tt"),
                          (("localization", "english", "te_miscellaneous_l_english.yml"), "sr_mod_queue_resort_tt")):
            with self.subTest(key=key):
                line = re.search(rf"(?m)^ {key}:0 \"(.*)\"$", _raw(*path)).group(1)
                self.assertNotIn("+3%", line)
                self.assertIn("$building_space_resort$", line)
        concepts = _raw("localization", "english", "te_concepts_l_english.yml")
        self.assertNotIn(" sr_module_resort:0", concepts)
        self.assertNotIn(" sr_module_resort_desc:0", concepts)


class ResortPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.display = _strip(_raw(*gss.DISPLAY_OUT.parts))  # gss.render_room_display (#1951)
        cls.gui = _raw("gui", "journal_entry_widgets", "space_race_widget.gui")
        cls.rows = _raw(*gss.GUI_OUT.parts)

    def test_display_values(self):
        for suffix in ("levels", "room", "draw", "queued", "next_draw", "past", "total", "split", "shown"):
            with self.subTest(value=suffix):
                _block(self.display, f"sr_disp_resort_{suffix}")
        nxt = _block(self.display, "sr_disp_resort_next_draw")
        self.assertIn("if = { limit = { sr_resort_queued_levels >= sr_resort_room_total } value = -75 }", nxt)
        self.assertIn("has_technology_researched = space_colonization", _block(self.display, "sr_disp_resort_shown"))
        self.assertIn("sr_resort_queued_levels > sr_resort_room_total", _block(self.display, "sr_disp_resort_past"))

    def test_overview_cell(self):
        self.assertIn('tooltip = "je_space_race_widget_ovc_resort_tt"', self.gui)
        self.assertIn('text = "je_space_race_widget_ovc_resort_cap"', self.gui)
        self.assertRegex(self.gui, r"visible = \"\[Or\( EqualTo_CFixedPoint\( Country\.MakeScope\.ScriptValue\('sr_disp_ebase_shown'\)"
                                   r"[^\n]*sr_disp_resort_shown")

    def test_summary_rows(self):
        self.assertIn('text = "je_space_race_widget_resort_label"', self.gui)
        self.assertIn('text = "je_space_race_widget_resort_queued_label"', self.gui)

    def test_generated_overrides(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertRegex(self.rows, rf"sr_disp_site_resort_room_{k}'\)\|0\]")
                # The draw with its Cultural Centers' points, read live (the owner, 2026-11-24).
                draw = f"[JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_site_resort_draw_{k}')|+0]"
                self.assertIn(f'raw_text = "({draw}%)"', self.rows)
                self.assertIn(f'raw_text = "#v {site.resort_room}#! ({draw}%)"', self.rows)
        self.assertIn('block "module_resorts"', self.gui)
        self.assertIn('block "module_draw"', self.gui)
        self.assertIn('block "site_resorts"', self.gui)

    def test_concept(self):
        concepts = _strip(_raw("common", "game_concepts", "extra_concepts.txt"))
        self.assertRegex(concepts, r"(?m)^concept_sr_resort_draw = \{\}")
        self.assertIn(' concept_sr_resort_draw:0 "Resort Draw"', _raw("localization", "english", "te_miscellaneous_l_english.yml"))
        self.assertIn(" concept_sr_resort_draw_desc:0 ", _raw("localization", "english", "te_concepts_l_english.yml"))



def _read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as f:
        return f.read()


def _containers(text, opener):
    """Each `opener = {` block's body, brace-matched."""
    for m in re.finditer(rf"\b{opener} = \{{", text):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        yield text[m.end():i - 1]


class ResortTextTest(unittest.TestCase):
    """What the final review of #1950 found in the panel, loc and guide."""

    def test_a_colony_page_row_holds_two_tiles(self):
        """te_sr_page_tile is 233 wide, so a 480 column holds two a row; the
        Resort Room tile must not push Terraformed past the panel's edge."""
        gui = _strip(_read("gui/journal_entry_widgets/space_race_widget.gui"))
        rows = 0
        for body in _containers(gui, "flowcontainer"):
            if "direction = horizontal" not in body.split("\n", 3)[1] + body.split("\n", 3)[0]:
                continue
            # the row's own tiles, not those of a container nested in it
            top, depth = [], 0
            for line in body.split("\n"):
                if depth == 0 and re.match(r"\s*te_sr_page_tile = \{", line):
                    top.append(line)
                depth += line.count("{") - line.count("}")
            if top:
                rows += 1
                self.assertLessEqual(len(top), 2, "a row of three 233-wide tiles overflows the 480 column")
        self.assertGreaterEqual(rows, 3)

    def test_the_building_name_is_never_pluralized_with_s(self):
        """"Resort Colonys": a name ending in -y takes no bare s."""
        for name in sorted(os.listdir(os.path.join(REPO, "localization", "english"))):
            if not name.endswith(".yml"):
                continue
            with self.subTest(file=name):
                text = _read(os.path.join("localization", "english", name))
                self.assertFalse("$building_space_resort$s" in text, f"{name} writes $building_space_resort$s")

    def test_the_draw_concept_gives_the_fill_order(self):
        """Colonies of positive draw fill before Earth orbit's 10 levels at 0."""
        text = _read("localization/english/te_concepts_l_english.yml")
        desc = re.search(r'^ concept_sr_resort_draw_desc:0 "(.*)"$', text, re.M).group(1)
        self.assertFalse("then each colony" in desc, "the concept puts Earth orbit first")
        self.assertTrue("ahead of" in desc, "the concept doesn't say what Earth orbit fills ahead of")

    def test_the_guide_lists_the_resort_colony(self):
        economy = _read("docs/player_guide/03-economy.md")
        self.assertRegex(economy, r"\| 0\.2 \| [^\n]*Resort Colonies")
        space = _read("docs/player_guide/16-space.md")
        ai = space[space.index("queues one module a year at each colony"):]
        ai = ai[:ai.index("\n\n")]
        self.assertTrue("Off-World Resort" in ai, "the AI's module plan leaves out the Off-World Resort")
        self.assertFalse("the rest of the Kuiper Belt" in space, "Proteus is a moon of Neptune")


if __name__ == "__main__":
    unittest.main()
