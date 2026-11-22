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

import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import gen_solar_sites as gss  # noqa: E402


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
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
                self.assertIn(f"multiply = sr_site_base_room_{k}", cap)
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


def gss_top():
    """The ladder's last step: 500 x 2^15 = 16.4 million a month, past every
    world's room together, so the room, not the ladder, stops +."""
    return 16


if __name__ == "__main__":
    unittest.main()
