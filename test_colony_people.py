# -*- coding: utf-8 -*-
"""Colony people limit modules (Part B of #1954).

Design: docs/superpowers/specs/2026-11-22-colony-people-limit-modules-design.md.
Slots go and crews limit a colony's modules: a crew is 10,000 people (5,000
with Artificial Intelligence), the Habitat is the one capped module, the five
slot technologies make Habitats roomier, settlers are an open-ended amount
drawn from every state and billed in Launch Capacity, and an Administration
costs authority. These tests hold the generated and hand-written script to
that rule.
"""

import glob
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
sys.path.insert(0, os.path.join(REPO, "scripts", "analysis"))

import gen_solar_sites as gss  # noqa: E402


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^\s*(?:[A-Z_]+:)?{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"no block {name}")
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[m.end():i - 1]


class CrewTest(unittest.TestCase):
    """Design § 4.2: a crew is 10,000 people, 5,000 with Artificial
    Intelligence, read through the world's holder; AI no longer waives crews."""

    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw(str(gss.VALUES_OUT)))
        cls.triggers = _strip(_raw(str(gss.TRIGGERS_OUT)))
        cls.effects = _strip(_raw(str(gss.EFFECTS_OUT)))
        cls.gui = _raw("gui", "journal_entry_widgets", "space_race_widget.gui")
        cls.display = _strip(_raw("common", "script_values", "space_race_display_values.txt"))

    def test_a_crew_is_ten_thousand_halved_by_ai(self):
        self.assertEqual(gss.CREW_PER_LEVEL, 10000)
        self.assertEqual(gss.AI_CREW_PER_LEVEL, 5000)
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                per = _block(self.values, f"sr_site_crew_per_level_{k}")
                self.assertIn("value = 10000", per)
                self.assertIn(f"global_var:sr_site_holder_{k} ?= {{ has_technology_researched = artificial_intelligence }}",
                              per)
                self.assertIn("value = 5000", per)
                crews = _block(self.values, f"sr_site_crews_{k}")
                self.assertIn(f"divide = sr_site_crew_per_level_{k}", crews)
        self.assertNotRegex(self.values, r"(?m)^sr_site_crew_per_level = ")

    def test_ai_no_longer_waives_crews(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertNotIn("artificial_intelligence", _block(self.values, f"sr_site_staffing_{k}"))
                self.assertNotIn("artificial_intelligence", _block(self.effects, f"sr_mod_ai_plan_{k}"))
        self.assertNotIn("sr_disp_agi", self.gui)
        self.assertNotIn("je_space_race_widget_settlers_agi", self.gui)
        self.assertNotRegex(self.display, r"(?m)^sr_disp_agi = ")


SLOT_TECHS = ("nuclear_thermal_propulsion", "orbital_manufacturing", "advanced_nanofabrication",
              "space_colonization", "molecular_assemblers")


def _tech_block(name):
    for era in ("era_11", "era_12", "era_13"):
        text = _strip(_raw("common", "technology", "technologies", f"{era}.txt"))
        if re.search(rf"(?m)^{name} = \{{", text):
            return _block(text, name)
    raise AssertionError(f"no technology {name}")


class HabitatRoomTest(unittest.TestCase):
    """Design §§ 4.4 and 5: a Habitat holds half the base room, +10 points for
    each of the five slot technologies, and the world keeps the best share it
    has had, so a cession or a break-away doesn't cut its people."""

    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw(str(gss.VALUES_OUT)))
        cls.effects = _strip(_raw(str(gss.EFFECTS_OUT)))
        cls.types = _strip(_raw("common", "modifier_type_definitions", "space_race_modifier_types.txt"))
        cls.modules = _strip(_raw("common", "scripted_effects", "sr_colony_module_effects.txt"))
        cls.module_values = _strip(_raw("common", "script_values", "sr_colony_module_values.txt"))

    def test_the_five_technologies_give_habitat_room(self):
        self.assertEqual(gss.HABITAT_MODIFIER, "country_sr_habitat_room_add")
        self.assertEqual(gss.HABITAT_BASE_SHARE, 0.5)
        for tech in SLOT_TECHS:
            with self.subTest(tech=tech):
                body = _tech_block(tech)
                self.assertIn("country_sr_habitat_room_add = 0.1", body)
                self.assertNotIn("country_sr_colony_slots_add", body)
        kind = _block(self.types, "country_sr_habitat_room_add")
        self.assertIn("script_only = yes", kind)
        self.assertIn("percent = yes", kind)
        self.assertNotIn("country_sr_colony_slots_add", self.types)

    def test_a_habitat_adds_the_world_s_share_of_its_base_room(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                now = _block(self.values, f"sr_site_hab_share_now_{k}")
                self.assertIn("value = 0.5", now)
                self.assertIn(f"global_var:sr_site_holder_{k} = {{ add = modifier:country_sr_habitat_room_add }}", now)
                share = _block(self.values, f"sr_site_hab_share_value_{k}")
                self.assertIn(f"value = sr_site_hab_share_now_{k}", share)
                self.assertIn(f"min = global_var:sr_site_hab_share_{k}", share)
                for room in (f"sr_site_room_{k}", f"sr_md_room_less_hab_{k}"):
                    body = _block(self.values, room)
                    self.assertIn(f"multiply = sr_site_hab_share_value_{k}", body)
                    self.assertNotIn("multiply = 0.5", body)

    def test_a_cession_keeps_the_room(self):
        """Review Focus 1: the record only rises. It is written only to the
        live share, which never falls below it, and cleared only on release."""
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                writes = re.findall(rf"set_global_variable = \{{ name = sr_site_hab_share_{k} value = (\S+) \}}",
                                    self.effects)
                self.assertEqual(writes, [f"sr_site_hab_share_value_{k}"])
                self.assertIn(f"name = sr_site_hab_share_{k} value = sr_site_hab_share_value_{k}",
                              _block(self.effects, f"sr_site_monthly_{k}"))
                self.assertIn(f"remove_global_variable = sr_site_hab_share_{k}",
                              _block(self.effects, f"sr_site_release_{k}"))
                self.assertEqual(len(re.findall(rf"remove_global_variable = sr_site_hab_share_{k}\b", self.effects)), 1)

    def test_the_marker_self_check_reads_the_habitat_room(self):
        check = _block(self.modules, "sr_marker_self_check")
        self.assertIn("TE_SELF_CHECK OK habitat_marker", check)
        self.assertNotIn("slot_marker", check)
        self.assertIn("modifier:country_sr_habitat_room_add", _block(self.module_values, "sr_habitat_room_modifier"))
        self.assertRegex(self.values, r"(?m)^sr_site_hab_share_seen = \{")
        self.assertNotIn("sr_site_slots_tech_seen", self.values)


ROOM_TECHS = ("space_colonization", "terraforming")


class BaseRoomTest(unittest.TestCase):
    """The owner, 2026-11-22: Space Colonization and Terraforming each give
    +50% of every colony's base room for people, so both double it, and the
    Habitats' and Terraforming's shares of it with it. Read through the
    holder, and the world keeps the best factor it has had, as the Habitat
    share does (design § 4.4)."""

    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw(str(gss.VALUES_OUT)))
        cls.effects = _strip(_raw(str(gss.EFFECTS_OUT)))
        cls.types = _strip(_raw("common", "modifier_type_definitions", "space_race_modifier_types.txt"))
        cls.loc = _raw("localization", "english", "te_modifiers_l_english.yml")

    def test_the_two_technologies_double_the_base_room(self):
        self.assertEqual(gss.ROOM_MODIFIER, "country_sr_colony_room_add")
        total = 0.0
        for tech in ROOM_TECHS:
            with self.subTest(tech=tech):
                found = re.findall(r"\bcountry_sr_colony_room_add = (\S+)", _tech_block(tech))
                self.assertEqual(found, ["0.5"])
                total += float(found[0])
        self.assertEqual(1 + total, 2.0)
        kind = _block(self.types, "country_sr_colony_room_add")
        self.assertIn("script_only = yes", kind)
        self.assertIn("percent = yes", kind)
        for key in ("country_sr_colony_room_add", "country_sr_colony_room_add_desc"):
            self.assertTrue(f" {key}:0 " in self.loc, f"no loc for {key}")

    def test_no_other_technology_carries_it(self):
        for era in ("era_11", "era_12", "era_13"):
            text = _strip(_raw("common", "technology", "technologies", f"{era}.txt"))
            for name in re.findall(r"(?m)^([a-z_\-]+) = \{", text):
                if name not in ROOM_TECHS:
                    self.assertNotIn("country_sr_colony_room_add", _block(text, name), name)

    def test_the_base_room_is_the_table_s_times_the_factor(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                now = _block(self.values, f"sr_site_room_mult_now_{k}")
                self.assertIn("value = 1", now)
                self.assertIn(f"global_var:sr_site_holder_{k} = {{ add = modifier:country_sr_colony_room_add }}", now)
                factor = _block(self.values, f"sr_site_room_mult_value_{k}")
                self.assertIn(f"value = sr_site_room_mult_now_{k}", factor)
                self.assertIn(f"min = global_var:sr_site_room_mult_{k}", factor)
                self.assertIn(f"sr_site_base_room_{k} = {{ value = sr_site_room_mult_value_{k} "
                              f"multiply = {site.room * 1000} }}", self.values)
                # Habitats and Terraforming are shares of the base room, so they grow with it.
                for room in (f"sr_site_room_{k}", f"sr_md_room_less_hab_{k}"):
                    self.assertIn(f"multiply = sr_site_base_room_{k}", _block(self.values, room))
        self.assertIn("add = modifier:country_sr_colony_room_add", _block(self.values, "sr_our_room_mult"))

    def test_a_cession_keeps_the_base_room(self):
        """The record only rises: written only to the live factor, which never
        falls below it, and cleared only on release."""
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                writes = re.findall(rf"set_global_variable = \{{ name = sr_site_room_mult_{k} value = (\S+) \}}",
                                    self.effects)
                self.assertEqual(writes, [f"sr_site_room_mult_value_{k}"])
                self.assertIn(f"name = sr_site_room_mult_{k} value = sr_site_room_mult_value_{k}",
                              _block(self.effects, f"sr_site_monthly_{k}"))
                self.assertIn(f"remove_global_variable = sr_site_room_mult_{k}",
                              _block(self.effects, f"sr_site_release_{k}"))
                self.assertEqual(len(re.findall(rf"remove_global_variable = sr_site_room_mult_{k}\b", self.effects)), 1)


def _walk_text(*dirs, exts=(".txt", ".gui")):
    for d in dirs:
        for root, _, files in os.walk(os.path.join(REPO, d)):
            for f in files:
                if f.endswith(exts):
                    path = os.path.join(root, f)
                    yield os.path.relpath(path, REPO), _strip(open(path, encoding="utf-8-sig").read())


class HabitatCapTest(unittest.TestCase):
    """Design §§ 4.1 and 4.3: no slots; any module may be queued at the flat
    price; the Habitat alone has a cap, the table's old slots, past which the
    n-th costs (1 + n) times the price while the module stock holds it."""

    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw(str(gss.VALUES_OUT)))
        cls.triggers = _strip(_raw(str(gss.TRIGGERS_OUT)))
        cls.effects = _strip(_raw(str(gss.EFFECTS_OUT)))
        cls.sguis = _strip(_raw("common", "scripted_guis", "sr_colony_sguis.txt"))

    def test_no_slot_reads_remain(self):
        self.assertFalse(hasattr(gss, "SLOTS_MODIFIER"))
        self.assertFalse(hasattr(gss, "SLOTS_PAST_MAX"))
        pattern = re.compile(r"sr_site_slots|sr_mod_slots_used|sr_site_slots_max|country_sr_colony_slots_add|sr_disp_ss_slots"
                             r"|sr_mod_scope_slot_room|sr_mod_scope_past_slots|sr_mod_generic_cost|sr_disp_site_slots")
        found = [path for path, text in _walk_text("common", "gui", "events") if pattern.search(text)]
        self.assertEqual(found, [])
        loc = _raw("localization", "english", "te_miscellaneous_l_english.yml")
        self.assertNotIn("sr_mod_req_slot_room_tt", loc)
        self.assertNotIn("sr_mod_queue_past_slots_tt", loc)

    def test_the_habitat_cap_is_the_table_s_slots(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(f"sr_site_hab_cap_{k} = {{ value = {site.slots} }}", self.values)

    def test_only_a_habitat_queue_checks_the_price(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                hab = _block(self.triggers, f"sr_mod_can_queue_hab_{k}")
                self.assertIn(f"sr_mod_next_hab_cost_{k} <= sr_mod_fab_stock_cap", hab)
                for t in gss.generic_types(site):
                    if t == "hab":
                        continue
                    body = _block(self.triggers, f"sr_mod_can_queue_{t}_{k}")
                    self.assertNotIn("cost", body)
                    self.assertNotIn("slots", body)

    def test_a_habitat_landing_always_installs(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                install = _block(self.effects, f"sr_mod_install_{k}")
                for t in gss.generic_types(site):
                    if t == "terra":
                        continue
                    self.assertIn(f"limit = {{ local_var:sr_ms_type_now = {gss.MODULE_CODES[t]} }}", install)

    def test_the_habitat_price_rises_past_the_cap(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                pending = _block(self.values, f"sr_site_hab_pending_{k}")
                self.assertIn(f"value = sr_site_hab_value_{k}", pending)
                self.assertIn(f"global_var:sr_site_ship_hab_{k}", pending)
                cost = _block(self.values, f"sr_mod_hab_cost_{k}")
                self.assertIn("value = sr_module_points", cost)
                self.assertIn(f"limit = {{ sr_site_hab_pending_{k} >= sr_site_hab_cap_{k} }} value = sr_site_hab_pending_{k} "
                              f"subtract = sr_site_hab_cap_{k} add = 2 multiply = sr_module_points", cost)
                used = _block(self.values, f"sr_mod_hab_used_{k}")
                self.assertIn(f"var:sr_mq_hab_{k}", used)
                nxt = _block(self.values, f"sr_mod_next_hab_cost_{k}")
                self.assertIn(f"limit = {{ sr_mod_hab_used_{k} >= sr_site_hab_cap_{k} }}", nxt)

    def test_only_a_habitat_head_pays_more(self):
        """Review Focus 4: every other queue head costs the flat price."""
        head = _block(self.values, "sr_mq_head_cost")
        self.assertIn("var:sr_mq_1_type = 3", head)
        self.assertNotIn(">= 3", head)
        self.assertIn("value = sr_mod_hab_cost_valles_marineris", head)
        test = gss.lunar_open_test("var:sr_mq_2_site", "var:sr_mq_2_type")
        self.assertIn("NOT = { var:sr_mq_2_type ?= 3 }", test)
        self.assertIn("sr_mod_fab_stock_value >= sr_mod_hab_cost_shackleton", test)

    def test_the_button_s_price_lines_are_the_habitat_s(self):
        self.assertRegex(self.triggers, r"(?m)^sr_mod_scope_past_hab_cap = \{")
        self.assertRegex(self.triggers, r"(?m)^sr_mod_scope_hab_price_fits = \{")
        module = _block(self.sguis, "sr_colony_module_sgui")
        self.assertIn("sr_mod_scope_hab_price_fits = yes", module)
        self.assertIn("sr_mod_scope_past_hab_cap = yes", module)
        self.assertRegex(module, r"limit = \{ scope:op = 3 \}\s*custom_tooltip = \{\s*text = sr_mod_req_hab_price_fits_tt")


class AdminAuthorityTest(unittest.TestCase):
    """Design § 7 (the owner, 2026-11-22: "~25 per level"): an Administration
    costs 25 authority a staffed level, a positive country_authority_cost_add,
    declared on the entry at sr_mod_units_admin; it stays a hook on autonomy."""

    def test_the_modifier_costs_25_authority(self):
        text = _strip(_raw("common", "static_modifiers", "space_race_modifiers.txt"))
        body = _block(text, "sr_module_admin")
        self.assertIn("country_authority_cost_add = 25", body)
        self.assertNotIn("country_authority_add", body)
        self.assertIn("icon = gfx/interface/icons/timed_modifier_icons/", body)

    def test_it_is_declared_at_the_staffed_levels(self):
        self.assertIn(("sr_module_admin", "sr_colonies_contested_enabled = yes sr_mod_units_admin > 0",
                       "sr_mod_units_admin"), gss.entry_declarations())
        self.assertFalse(gss.FACILITY["admin"].modifier)
        self.assertTrue(gss.FACILITY["admin"].bills)
        declared = _strip(_raw("common", "journal_entries", "sr_sites_generated.txt"))
        self.assertIn("modifier = sr_module_admin", declared)

    def test_it_still_lowers_autonomy(self):
        values = _strip(_raw(str(gss.VALUES_OUT)))
        self.assertIn("sr_site_admin_value_valles_marineris", values)
        loc = _raw("localization", "english", "te_concepts_l_english.yml")
        for key in ("sr_module_admin", "sr_module_admin_desc"):
            self.assertTrue(re.search(rf"(?m)^ {key}:0 ", loc), f"no loc for {key}")


class ColonyAiTest(unittest.TestCase):
    """Design § 9: the AI and a colony's own builds stay within the Habitat cap
    and their crews; an Administration waits for twice its authority; the
    automatic pick weighs the people a world holds at its cap."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw(str(gss.EFFECTS_OUT)))
        cls.values = _strip(_raw(str(gss.VALUES_OUT)))
        cls.module_values = _strip(_raw("common", "script_values", "sr_colony_module_values.txt"))

    def _branches(self, body):
        return re.findall(r"limit = \{(.*?)\}\s*(sr_mod_queue = \{ KEY = \w+ TYPE = (\w+) )", body, re.S)

    def test_the_ai_plan_keeps_its_habitat_in_the_cap_and_the_rest_in_its_crews(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                body = _block(self.effects, f"sr_mod_ai_plan_{k}")
                branches = self._branches(body)
                self.assertTrue(branches)
                for limit, _, t in branches:
                    self.assertNotIn("slots", limit)
                    if t == "hab":
                        self.assertIn(f"sr_mod_hab_used_{k} < sr_site_hab_cap_{k}", limit)
                        self.assertIn(f"sr_site_fill_{k} >= 0.75", limit)
                    else:
                        self.assertIn(f"sr_site_crews_{k} >= sr_site_levels_{k}", limit)
                    if t == "admin":
                        self.assertIn("authority >= sr_mod_ai_admin_authority", limit)
        self.assertIn("sr_mod_ai_admin_authority = { value = 50 }", self.module_values)

    def test_a_colony_s_own_builds_stay_in_the_cap_and_its_crews(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                body = _block(self.effects, f"sr_site_self_build_{k}")
                limits = re.findall(r"limit = \{(.*?)\}", body, re.S)
                hab = [lim for lim in limits if f"sr_mod_hab_used_{k}" in lim]
                self.assertEqual(len(hab), 1)
                self.assertIn(f"sr_mod_hab_used_{k} < sr_site_hab_cap_{k}", hab[0])
                others = [lim for lim in limits if "sr_mod_spec_used" in lim or "sr_site_lab_value" in lim]
                self.assertTrue(others)
                for lim in others:
                    self.assertIn(f"sr_site_crews_{k} >= sr_site_levels_{k}", lim)

    def test_the_pick_weighs_the_people_at_the_cap(self):
        self.assertEqual(gss.SCORE_PER_CREW_ROOM, 1)
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                cap = _block(self.values, f"sr_site_people_at_cap_{k}")
                self.assertIn("value = 0.5", cap)
                self.assertIn(f"add = modifier:{gss.HABITAT_MODIFIER}", cap)
                self.assertIn(f"multiply = sr_site_hab_cap_{k}", cap)
                self.assertIn("add = 1", cap)
                # At THIS's base room factor, not the world's holder's.
                self.assertIn(f"multiply = {site.room * 1000}", cap)
                self.assertIn("multiply = sr_our_room_mult", cap)
                self.assertNotIn("sr_site_base_room", cap)
                score = _block(self.values, f"sr_cf_score_{k}")
                self.assertIn(f"add = {{ value = sr_site_people_at_cap_{k} divide = 10000 }}", score)


class SettlerAmountTest(unittest.TestCase):
    """Design § 6.1: step n sends 500 x 2^(n - 1) a month (1, 2 and 3 keep
    today's Low, Steady and High); - halves to Off, + doubles while the amount
    is below the open colonies' free room; the panel shows the number."""

    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw("common", "script_values", "sr_colony_population_values.txt"))
        cls.effects = _strip(_raw("common", "scripted_effects", "sr_colony_population_effects.txt"))
        cls.sguis = _strip(_raw("common", "scripted_guis", "sr_colony_sguis.txt"))

    def test_the_amount_doubles_from_500(self):
        ladder = _block(self.values, "sr_emig_level_batches")
        steps = {int(n): int(v) for n, v in re.findall(r"sr_emig_level_value = (\d+) \} value = (\d+)", ladder)}
        self.assertEqual(steps[1], 1)
        self.assertEqual(steps[2], 2)
        self.assertEqual(steps[3], 4)
        self.assertEqual(steps[8], 128)
        self.assertEqual(sorted(steps), list(range(1, gss_top() + 1)))
        for n, batches in steps.items():
            self.assertEqual(batches, 2 ** (n - 1), n)
        amount = _block(self.values, "sr_emig_amount")
        self.assertIn("value = sr_emig_level_batches", amount)
        self.assertIn("multiply = sr_emig_batch_people", amount)

    def test_minus_halves_to_off_and_plus_doubles(self):
        step = _block(self.effects, "sr_emig_step_level")
        self.assertRegex(step, r"limit = \{ sr_emig_level_value <= 1 \}\s*sr_emig_set_level = \{ LEVEL = 0 \}")
        self.assertIn("change_variable = { name = sr_emig_level subtract = 1 }", step)
        self.assertIn("change_variable = { name = sr_emig_level add = 1 }", step)
        self.assertIn(f"sr_emig_level_value < {gss_top()}", step)

    def test_plus_is_valid_below_the_open_room(self):
        sgui = _block(self.sguis, "sr_settlers_sgui")
        self.assertRegex(sgui, r"text = sr_emig_room_used_tt\s*sr_emig_amount < sr_emig_open_room_total")
        self.assertNotIn("sr_emig_at_highest_tt", sgui)
        self.assertNotIn("sr_emig_level_value <= 2", sgui)
        loc = _raw("localization", "english", "te_miscellaneous_l_english.yml")
        self.assertFalse("sr_emig_at_highest_tt" in loc, "sr_emig_at_highest_tt is still in the loc")
        self.assertTrue(" sr_emig_room_used_tt:0 " in loc, "no loc for sr_emig_room_used_tt")

    def test_the_panel_shows_the_amount(self):
        gui = _raw("gui", "journal_entry_widgets", "space_race_widget.gui")
        self.assertTrue("ScriptValue('sr_disp_emig_amount')" in gui, "the stepper doesn't show the amount")
        for n in (1, 2, 3):
            self.assertFalse(f"je_space_race_widget_emig_level_{n}" in gui, f"level name {n} still shown")
        display = _strip(_raw("common", "script_values", "space_race_display_values.txt"))
        self.assertTrue("sr_disp_emig_amount = { value = sr_emig_amount }" in display, "no sr_disp_emig_amount")


SPACE_PROGRAM_GROUPS = ("pmg_base_building_space_program", "pmg_space_program_debris_removal",
                        "pmg_space_program_module_fabrication", "pmg_space_program_module_storage",
                        "pmg_space_program_mission_ceiling")


def _space_program_launch_capacity():
    """{method: its goods_input_launch_capacity_add} for every Space Program
    method with one, read from the method groups and the methods' files."""
    groups = "".join(_strip(open(f, encoding="utf-8-sig").read())
                     for f in glob.glob(os.path.join(REPO, "common", "production_method_groups", "*.txt")))
    methods = "".join(_strip(open(f, encoding="utf-8-sig").read())
                      for f in glob.glob(os.path.join(REPO, "common", "production_methods", "*.txt")))
    out = {}
    for group in SPACE_PROGRAM_GROUPS:
        listed = re.search(r"production_methods = \{([^}]*)\}", _block(groups, group)).group(1).split()
        for method in listed:
            lc = re.search(r"goods_input_launch_capacity_add = (\d+)", _block(methods, method))
            if lc:
                out[method] = int(lc.group(1))
    return out


class SettlerBillTest(unittest.TestCase):
    """Design § 6.2: 3 Launch Capacity a settler, on the Space Program as a
    goods_input_launch_capacity_mult at 100 x the week's bill / (its Launch
    Capacity x (1 + the country's throughput)), from one refresh site; the
    emigration programme's throughput goes."""

    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw("common", "script_values", "sr_colony_population_values.txt"))
        cls.effects = _strip(_raw("common", "scripted_effects", "sr_colony_population_effects.txt"))
        cls.modifiers = _strip(_raw("common", "static_modifiers", "space_race_modifiers.txt"))

    def test_the_base_reads_every_method_s_launch_capacity(self):
        expected = _space_program_launch_capacity()
        self.assertEqual(len(expected), 13)  # six missions, three debris, three fabrication, the Orbital Depot
        base = _block(self.values, "sr_emig_lc_base")
        found = {m: int(v) for m, v in re.findall(
            r"has_active_production_method = (\w+) \} \} add = (\d+)", base)}
        self.assertEqual(found, expected)

    def test_the_units_divide_out_the_throughput(self):
        self.assertIn("sr_emig_lc_per_settler = { value = 3 }", self.values)
        week = _block(self.values, "sr_emig_bill_week")
        for term in ("value = var:sr_emig_last_sent", "multiply = sr_emig_lc_per_settler", "multiply = 12",
                     "divide = 52"):
            self.assertIn(term, week)
        divisor = _block(self.values, "sr_emig_bill_divisor")
        for term in ("value = modifier:building_space_program_throughput_add", "add = 1",
                     "multiply = sr_emig_lc_base", "min = 1"):
            self.assertIn(term, divisor)
        units = _block(self.values, "sr_emig_bill_units_value")
        for term in ("value = sr_emig_bill_week", "multiply = 100", "divide = sr_emig_bill_divisor"):
            self.assertIn(term, units)

    def test_one_refresh_removes_first_and_adds_only_above_zero(self):
        refresh = _block(self.effects, "sr_emig_bill_refresh")
        self.assertLess(refresh.index("remove_modifier"), refresh.index("add_modifier"))
        self.assertIn("every_scope_building = {", refresh)
        self.assertIn("is_building_type = building_space_program", refresh)
        self.assertRegex(refresh, r"limit = \{ root\.var:sr_emig_bill_units > 0 \}\s*add_modifier = \{ "
                                  r"name = sr_settler_launches multiplier = root\.var:sr_emig_bill_units \}")
        self.assertEqual(refresh.count("add_modifier"), 1)
        je = _strip(_raw("common", "journal_entries", "je_space_race.txt"))
        pulse = je[je.index("sr_emig_month = yes"):]
        self.assertTrue(pulse.lstrip().split("\n", 1)[1].lstrip().startswith("sr_emig_bill_refresh = yes"))
        found = [path for path, text in _walk_text("common", "events") if "add_modifier = { name = sr_settler_launches" in text]
        self.assertEqual(found, ["common/scripted_effects/sr_colony_population_effects.txt"])

    def test_the_bill_comes_off_once_settlers_stop(self):
        """Review Focus 3: the sent lasts 40 days, past a month's pulse, and the
        always-on pulse takes the bill off a country whose sent has lapsed."""
        month = _block(self.effects, "sr_emig_month")
        self.assertIn("set_variable = { name = sr_emig_last_sent value = local_var:sr_emig_sent days = 40 }", month)
        always = _strip(_raw("common", "on_actions", "space_race_on_actions.txt"))
        self.assertRegex(always, r"NOT = \{ has_variable = sr_emig_last_sent \}\s*any_scope_building = \{\s*"
                                 r"is_building_type = building_space_program\s*has_modifier = sr_settler_launches")
        self.assertIn("remove_modifier_if_exists_effect = { MODIFIER = sr_settler_launches }", always)

    def test_the_modifier_and_the_old_throughput(self):
        body = _block(self.modifiers, "sr_settler_launches")
        self.assertIn("goods_input_launch_capacity_mult = 0.01", body)
        found = [path for path, text in _walk_text("common", "events", "gui", exts=(".txt", ".gui", ".yml"))
                 if "sr_emigration_programme" in text]
        self.assertEqual(found, [])
        self.assertFalse("sr_emigration_programme" in _raw("localization", "english", "te_concepts_l_english.yml"),
                         "sr_emigration_programme's loc is left")
        import gen_nation_tab
        self.assertIn("sr_settler_launches", gen_nation_tab.NOT_ON_COUNTRY)


class AiSettlersTest(unittest.TestCase):
    """Design § 9 (the owner, on the builder check: "Share fabrication's 5%"):
    an AI's settlers take the largest step whose weekly bill at today's Launch
    Capacity price fits in fabrication's 5% of its weekly fixed income less the
    chosen method's bill, never past the open room; at least step 1 for a
    tending AI with a positive income, step 1 for any other; Off as before."""

    FABRICATION = ("orbital_assembly", "lunar_foundries", "fusion_shipyards")

    @classmethod
    def setUpClass(cls):
        cls.pop_values = _strip(_raw("common", "script_values", "sr_colony_population_values.txt"))
        cls.mod_values = _strip(_raw("common", "script_values", "sr_colony_module_values.txt"))
        cls.effects = _strip(_raw("common", "scripted_effects", "sr_colony_population_effects.txt"))

    def test_the_room_is_the_budget_less_the_method_s_bill(self):
        now = _block(self.mod_values, "sr_mod_ai_fab_bill_now")
        self.assertIn("value = 0", now)
        for key in self.FABRICATION:
            self.assertIn(f"has_active_production_method = pm_sr_fabrication_{key} }} }}", now)
            self.assertIn(f"value = sr_mod_fab_bill_base_{key}", now)
        self.assertIn("multiply = sr_mod_fab_bill_price_factor", now)
        self.assertIn("sr_mod_fab_bill_base_orbital_assembly = { value = 340000 }", self.mod_values)
        room = _block(self.pop_values, "sr_emig_ai_room")
        self.assertIn("value = sr_mod_ai_fab_budget", room)
        self.assertIn("subtract = sr_mod_ai_fab_bill_now", room)

    def test_a_step_s_bill_at_today_s_price(self):
        import pm_costs
        price = pm_costs.load_goods()["launch_capacity"]
        week = _block(self.pop_values, "sr_emig_ai_week_cost")
        for term in ("value = sr_emig_batch_people", "multiply = sr_emig_lc_per_settler", "multiply = 12",
                     "divide = 52", f"multiply = {price}", "add = sr_launch_capacity_price_up"):
            self.assertIn(term, week)

    def test_the_largest_step_that_fits(self):
        step = _block(self.pop_values, "sr_emig_ai_step")
        self.assertIn("value = 1", step)
        found = re.findall(r"if = \{ limit = \{ sr_emig_ai_fits >= (\d+) sr_emig_open_room_total >= (\d+) \} "
                           r"value = (\d+) \}", step)
        self.assertEqual([int(n) for _, _, n in found], list(range(2, gss_top() + 1)))
        for fits, room, n in found:
            n = int(n)
            self.assertEqual(int(fits), 2 ** (n - 1))
            self.assertEqual(int(room), 500 * 2 ** (n - 1))
        self.assertNotIn("else_if", step)
        fits = _block(self.pop_values, "sr_emig_ai_fits")
        self.assertIn("value = sr_emig_ai_room", fits)
        self.assertIn("divide = sr_emig_ai_week_cost", fits)

    def test_the_review(self):
        review = _block(self.effects, "sr_emig_ai_review")
        self.assertIn("sr_emig_open_room_total < sr_emig_batch_people", review)
        self.assertIn("in_default = yes", review)
        self.assertRegex(review, r"sr_ai_tends_colonies = yes\s*net_fixed_income > 0\s*\}\s*"
                                 r"if = \{\s*limit = \{ NOT = \{ sr_emig_level_value = sr_emig_ai_step \} \}\s*"
                                 r"sr_emig_set_level = \{ LEVEL = sr_emig_ai_step \}")
        self.assertIn("sr_emig_set_level = { LEVEL = 1 }", review)
        self.assertNotIn("LEVEL = 2", review)
        je = _strip(_raw("common", "journal_entries", "je_space_race.txt"))
        self.assertLess(je.index("sr_mod_ai_review = yes"), je.index("sr_emig_ai_review = yes"))
        self.assertLess(je.index("sr_emig_ai_review = yes"), je.index("sr_emig_month = yes"))


class ModulesViewTest(unittest.TestCase):
    """Design § 10: a colony's header line reads Crews needed / available (red
    when short) with the share, and Habitats against the cap; its page's Crews
    tile the same; the + button says whether a crewed module has a crew; the
    level field takes two digits."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _strip(_raw("gui", "journal_entry_widgets", "space_race_widget.gui"))
        cls.rows = _strip(_raw(str(gss.GUI_OUT)))
        cls.display = _strip(_raw(str(gss.DISPLAY_OUT)))
        cls.sguis = _strip(_raw("common", "scripted_guis", "sr_colony_sguis.txt"))
        cls.triggers = _strip(_raw(str(gss.TRIGGERS_OUT)))

    def test_the_crews_values(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(f"sr_disp_site_crews_needed_{k} = {{ value = sr_site_crew_needed_{k} }}", self.display)
                self.assertIn(f"sr_disp_site_crews_{k} = {{ value = sr_site_crews_{k} }}", self.display)
                short = _block(self.display, f"sr_disp_site_crews_short_{k}")
                self.assertIn(f"limit = {{ sr_site_crew_needed_{k} > sr_site_crews_{k} }} value = 1", short)

    def test_the_header_cell_and_the_page_tile(self):
        row = _block(self.gui, "type te_sr_colony_row") if "type te_sr_colony_row = {" in self.gui else self.gui
        for needle in ('block "module_crews" {}', 'block "module_crews_short" {}',
                       'text = "je_space_race_widget_modules_col_crews"',
                       'tooltip = "je_space_race_widget_modules_crews_tt"'):
            self.assertGreaterEqual(row.count(needle), 1 if "col_crews" in needle else 2, needle)
        self.assertFalse("je_space_race_widget_modules_col_staffing" in self.gui, "the Staffing label is left")
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(f"ScriptValue('sr_disp_site_crews_short_{k}'), '(CFixedPoint)0' )]", self.rows)
                self.assertIn(f"ScriptValue('sr_disp_site_crews_short_{k}'), '(CFixedPoint)1' )]", self.rows)
        loc = _raw("localization", "english", "te_journal_entries_l_english.yml")
        for key in ("je_space_race_widget_modules_col_crews", "je_space_race_widget_modules_crews_tt"):
            self.assertTrue(f" {key}:0 " in loc, f"no loc for {key}")

    def test_the_plus_button_says_whether_a_crew_is_free(self):
        self.assertRegex(self.triggers, r"(?m)^sr_mod_scope_crew_spare = \{")
        for site in gss.SITES:
            self.assertIn(f"AND = {{ scope:site = {site.index} sr_site_crews_{site.key} >= sr_mod_crewed_pending_{site.key} }}",
                          _block(self.triggers, "sr_mod_scope_crew_spare"))
        module = _block(self.sguis, "sr_colony_module_sgui")
        self.assertRegex(module, r"sr_mod_scope_crew_spare = yes\s*\}\s*custom_tooltip = sr_mod_queue_crew_spare_tt")
        self.assertIn("custom_tooltip = sr_mod_queue_crew_short_tt", module)
        loc = _raw("localization", "english", "te_miscellaneous_l_english.yml")
        for key in ("sr_mod_queue_crew_spare_tt", "sr_mod_queue_crew_short_tt"):
            self.assertTrue(f" {key}:0 " in loc, f"no loc for {key}")

    def test_the_level_takes_two_digits(self):
        import test_space_race_labels as L
        holder = [c for c in vars(L).values() if isinstance(c, type) and "CELL" in vars(c)][0]
        self.assertEqual(holder.CELL["cell_level"], "88")


class PeopleViewTest(unittest.TestCase):
    """Design § 10: the programme line shows the amount, last month's sent and
    the week's Launch Capacity; each colony its crews used / available,
    colored by the crews left once its queue lands; the overview a cell while any colony is short; and the
    Habitat cap, with the people and crews it holds at our share, wherever a
    destination is picked (the owner)."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _strip(_raw("gui", "journal_entry_widgets", "space_race_widget.gui"))
        cls.rows = _strip(_raw(str(gss.GUI_OUT)))
        cls.display = _strip(_raw(str(gss.DISPLAY_OUT)))
        cls.loc = _raw("localization", "english", "te_journal_entries_l_english.yml")

    def _has_loc(self, key):
        self.assertTrue(f" {key}:0 " in self.loc, f"no loc for {key}")

    def test_the_programme_line(self):
        for value in ("sr_disp_emig_last_sent", "sr_disp_emig_bill_week"):
            self.assertTrue(f"ScriptValue('{value}')" in self.loc, value)
        for key in ("je_space_race_widget_emig_sent_label", "je_space_race_widget_emig_sent_figure",
                    "je_space_race_widget_emig_bill_label", "je_space_race_widget_emig_bill_figure"):
            self._has_loc(key)
            self.assertTrue(f'"{key}"' in self.gui, f"{key} isn't shown")

    def test_each_colony_shows_its_crews_used_of_available(self):
        """The owner, 2026-11-23: used / available, green with crews to spare
        once the queue and every shipment land, yellow with exactly enough, red short."""
        for block in ("settler_crews", "settler_crews_exact", "settler_crews_short"):
            self.assertTrue(f'block "{block}" {{}}' in self.gui, f"no {block} cell")
        rows = _raw(str(gss.GUI_OUT))  # unstripped: the figure's color code reads as a comment to _strip
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                planned = _block(self.display, f"sr_site_crews_planned_{k}")
                self.assertIn(f"value = sr_mod_crewed_pending_{k}", planned)
                self.assertIn("subtract = 1", planned)
                fit = _block(self.display, f"sr_disp_site_crews_fit_{k}")
                self.assertIn(f"if = {{ limit = {{ sr_site_crews_planned_{k} = sr_site_crews_{k} }} value = 1 }}", fit)
                self.assertIn(f"else_if = {{ limit = {{ sr_site_crews_planned_{k} > sr_site_crews_{k} }} value = 2 }}", fit)
                used = (f"[JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_site_crews_needed_{k}')|0]/"
                        f"[JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_site_crews_{k}')|0]")
                # `yellow`, not `Y`: `#Y` is vanilla's zero-value format and draws white (from #2016).
                for block, value, color in (("settler_crews", 0, "G"), ("settler_crews_exact", 1, "yellow"),
                                            ("settler_crews_short", 2, "R")):
                    self.assertIn(f'blockoverride "{block}" {{\n\t\t\t\tvisible = "[EqualTo_CFixedPoint( '
                                  f"JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_site_crews_fit_{k}'), "
                                  f"'(CFixedPoint){value}' )]\"\n\t\t\t\traw_text = \"#{color} {used}#!\"", rows)

    def test_the_overview_counts_the_understaffed(self):
        count = _block(self.display, "sr_disp_understaffed_count")
        for site in gss.SITES:
            k = site.key
            self.assertIn(f"if = {{ limit = {{ global_var:sr_site_holder_{k} ?= this sr_site_crew_needed_{k} > sr_site_crews_{k} }} "
                          "add = 1 }", count)
        self.assertTrue("ScriptValue('sr_disp_understaffed_count'), '(CFixedPoint)1' )]" in self.gui, "no overview cell")
        for key in ("je_space_race_widget_ovc_crews_cap", "je_space_race_widget_ovc_crews_word",
                    "je_space_race_widget_ovc_crews_fig", "je_space_race_widget_ovc_crews_tt"):
            self._has_loc(key)

    def test_the_cap_where_a_destination_is_picked(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(f"sr_disp_ss_people_at_cap_{k} = {{ value = sr_site_people_at_cap_{k} floor = yes }}", self.display)
                crews = _block(self.display, f"sr_disp_ss_crews_at_cap_{k}")
                self.assertIn(f"value = sr_site_people_at_cap_{k}", crews)
                self.assertIn(f"has_technology_researched = {gss.AI_CREW_TECH}", crews)
                self.assertIn(f'tooltip = "je_space_race_widget_ss_habs_tt_{k}"', self.rows)
                hover = self.loc[self.loc.index(f" je_space_race_widget_ss_habs_tt_{k}:0 "):].split("\n", 1)[0]
                for value in (f"sr_disp_ss_people_at_cap_{k}", f"sr_disp_ss_crews_at_cap_{k}", "sr_disp_our_hab_share"):
                    self.assertIn(value, hover)
                self.assertIn(f"#v {site.slots}#!", hover)
        self.assertTrue('block "site_slots_tooltip" {' in self.gui, "the cap cell's hover is fixed")
        target = _block(self.display, "sr_disp_cf_target_people_at_cap")
        self.assertIn("var:sr_cf_target = 1", target)
        self.assertIn("value = sr_disp_ss_people_at_cap_valles_marineris", target)
        self.assertTrue('tooltip = "je_space_race_widget_cf_target_habs_tt"' in self.gui, "no hover on the target line")
        self._has_loc("je_space_race_widget_cf_target_habs_tt")


def gss_top():
    """The ladder's last step: 500 x 2^15 = 16.4 million a month, past every
    world's room together, so the room, not the ladder, stops +."""
    return 16



class ReviewFixesTest(unittest.TestCase):
    """The final review's findings (PR #1958): Defences thin with a short crew,
    the + button's crew line counts what is on its way, and the Habitat and
    Spaceport text no longer speaks of slots or a fixed half."""

    @classmethod
    def setUpClass(cls):
        cls.values = _strip(_raw(str(gss.VALUES_OUT)))
        cls.display = _strip(_raw("common", "script_values", "sr_sites_display_generated.txt"))
        cls.triggers = _strip(_raw(str(gss.TRIGGERS_OUT)))
        cls.loc = "".join(_raw(p) for p in glob.glob(os.path.join(REPO, "localization", "english", "*.yml")))

    def test_defences_run_at_the_colony_s_staffing(self):
        """Design § 4.1: every crewed level, Defences included, runs at the
        shared staffing share, so Defences past the crews add little."""
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                staffed = _block(self.values, f"sr_site_def_staffed_{k}")
                self.assertIn(f"value = sr_site_def_value_{k}", staffed)
                self.assertIn(f"multiply = sr_site_staffing_{k}", staffed)
                # Every reader goes through the staffed levels (shared ones too, on the
                # Moon and Mars: test_solar_sites.SharedWorldTest).
                self.assertIn(f"value = sr_site_def_staffed_{k}", _block(self.values, f"sr_site_def_shared_{k}"))
                self.assertIn(f"value = sr_site_def_shared_{k}", _block(self.values, f"sr_site_def_fire_{k}"))
                for name in (f"sr_site_hardness_{k}", f"sr_site_target_strength_{k}"):
                    self.assertIn(f"sr_site_def_staffed_{k}\n", _block(self.values, name), name)
                    self.assertNotIn(f"sr_site_def_value_{k}", _block(self.values, name), name)

    def test_the_crew_line_counts_the_modules_on_their_way(self):
        spare = _block(self.triggers, "sr_mod_scope_crew_spare")
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(f"sr_site_crews_{k} >= sr_mod_crewed_pending_{k}", spare)
                body = _block(self.values, f"sr_mod_crewed_pending_{k}")
                self.assertIn(f"value = sr_site_levels_{k}", body)
                for t in ("a", "b", *gss.generic_types(site)):
                    queued = f"add = var:sr_mq_{t}_{k}"
                    shipped = f"add = global_var:sr_site_ship_{t}_{k}"
                    if t == "hab":
                        self.assertNotIn(queued, body)
                    else:
                        self.assertIn(queued, body)
                        self.assertIn(shipped, body)

    def test_the_habitat_and_spaceport_text_is_current(self):
        port = re.search(r'(?m)^ je_space_race_widget_mod_port_tt:0 "([^\n]*)"', self.loc).group(1)
        self.assertNotIn("slot", port)
        hab = re.search(r'(?m)^ sr_mod_queue_hab_tt:0 "([^\n]*)"', self.loc).group(1)
        self.assertNotIn("half", hab)


if __name__ == "__main__":
    unittest.main()
