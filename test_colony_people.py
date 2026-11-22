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


if __name__ == "__main__":
    unittest.main()
