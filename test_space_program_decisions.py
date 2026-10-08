"""The decisions that found and advance the Space Program, and establish the
Strategic Reserve (common/decisions/extra_decisions.txt).

Each "Begin the X" mission decision switches the Space Program to one
production method. Its technology, the programme bools it reads and the
milestones it waits for are copies of facts held in extra_pms.txt and
je_space_race.txt, and the AI's bill estimate copies each method's Launch
Capacity input. A change on either side would leave a decision offering the
wrong mission, or weighing the wrong bill, with no error from the engine.
These tests hold the copies to their sources.
"""

import re
import unittest
from pathlib import Path

from test_nuclear_deterrence import block, loc_keys, loc_value, read, strip_comments

ROOT = Path(__file__).resolve().parent
DECISIONS = ROOT / "common/decisions/extra_decisions.txt"
PMS = ROOT / "common/production_methods/extra_pms.txt"
PMGS = ROOT / "common/production_method_groups/extra_pm_groups.txt"
JES = ROOT / "common/journal_entries/je_space_race.txt"
VALUES = ROOT / "common/script_values/space_race_values.txt"
HUB = ROOT / "common/buildings/strategic_reserve.txt"
BUILDINGS = ROOT / "common/buildings/extra_buildings.txt"

# decision -> (production method it activates, the method it builds on).
# The base is the mission the programme must run for the decision to show
# (its bool held, the target's not): the one below on the Earth Orbit ->
# Moon -> Mars -> Solar Colonization ladder, and Mars for Deep Space
# Exploration and the Interstellar Mission, which may follow any mission
# from Mars up (see the header comment in extra_decisions.txt).
MISSIONS = {
    "te_decision_space_mission_moon": ("pm_moon_mission", "pm_earth_orbit"),
    "te_decision_space_mission_mars": ("pm_mars_mission", "pm_moon_mission"),
    "te_decision_space_mission_solar": ("pm_solar_colonization", "pm_mars_mission"),
    "te_decision_space_mission_deep_space": ("pm_deep_space_exploration", "pm_mars_mission"),
    "te_decision_space_mission_interstellar": ("pm_interstellar_mission", "pm_mars_mission"),
}
LADDER = ["pm_earth_orbit", "pm_moon_mission", "pm_mars_mission",
          "pm_solar_colonization", "pm_deep_space_exploration", "pm_interstellar_mission"]
UNITS_VALUE = {
    "pm_earth_orbit": "sr_mission_units_earth_orbit",
    "pm_moon_mission": "sr_mission_units_moon",
    "pm_mars_mission": "sr_mission_units_mars",
    "pm_solar_colonization": "sr_mission_units_solar",
    "pm_deep_space_exploration": "sr_mission_units_deep_space",
    "pm_interstellar_mission": "sr_mission_units_interstellar",
}
# The milestones on the owner's rule "the milestones the current mission
# serves are complete", for the decisions that follow it.
OWNER_RULE = ("te_decision_space_mission_moon", "te_decision_space_mission_mars",
              "te_decision_space_mission_solar")


def bool_of(pm):
    return f"country_sr_{pm[len('pm_'):]}_program_bool"


def positive_completions(text):
    """`has_variable = sr_completed_X` outside a NOT."""
    text = re.sub(r"NOT\s*=\s*\{\s*has_variable\s*=\s*sr_completed_\w+\s*\}", "", text)
    return set(re.findall(r"has_variable\s*=\s*sr_completed_(\w+)", text))


class SpaceMissionDecisionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decisions = strip_comments(read(DECISIONS))
        cls.pms = strip_comments(read(PMS))
        cls.jes = strip_comments(read(JES))
        cls.values = strip_comments(read(VALUES))
        # milestone -> (completions its `possible` requires, bools it reads)
        cls.milestones = {}
        for name in re.findall(r"^je_space_race_(\w+)\s*=\s*\{", cls.jes, re.M):
            possible = block(block(cls.jes, f"je_space_race_{name}"), "possible")
            bools = set(re.findall(r"modifier:(country_sr_\w+_program_bool)\s*=\s*yes", possible))
            if bools:
                cls.milestones[name] = (positive_completions(possible), bools)

    def closure(self, completions):
        """A completion implies every completion its milestone required."""
        done, todo = set(), list(completions)
        while todo:
            m = todo.pop()
            if m in done:
                continue
            done.add(m)
            todo.extend(self.milestones.get(m, (set(), set()))[0])
        return done

    def served(self, pm):
        """Milestones whose `possible` reads this method's own bool."""
        return {m for m, (_, bools) in self.milestones.items() if bool_of(pm) in bools}

    def test_the_journal_entries_read_every_mission(self):
        for pm in LADDER:
            with self.subTest(pm=pm):
                self.assertTrue(self.served(pm), f"no milestone reads {bool_of(pm)}")

    def test_each_method_carries_every_lower_bool(self):
        # Switching up must never stop a running milestone.
        for i, pm in enumerate(LADDER):
            unscaled = block(block(block(self.pms, pm), "country_modifiers"), "unscaled")
            for lower in LADDER[:i + 1]:
                with self.subTest(pm=pm, lower=lower):
                    self.assertIn(f"{bool_of(lower)} = yes", unscaled)

    def test_decision_activates_its_method(self):
        for name, (pm, _) in MISSIONS.items():
            with self.subTest(decision=name):
                when = block(block(self.decisions, name), "when_taken")
                self.assertRegex(when, r"building_type\s*=\s*building_space_program")
                self.assertRegex(when, r"production_method\s*=\s*" + pm + r"\b")

    def test_decision_shows_at_the_methods_technology(self):
        for name, (pm, _) in MISSIONS.items():
            with self.subTest(decision=name):
                techs = re.findall(r"\w+", block(block(self.pms, pm), "unlocking_technologies"))
                self.assertEqual(len(techs), 1)
                shown = block(block(self.decisions, name), "is_shown")
                self.assertIn(f"has_technology_researched = {techs[0]}", shown)

    def test_decision_shows_on_its_base_mission_only(self):
        for name, (pm, base) in MISSIONS.items():
            with self.subTest(decision=name):
                shown = block(block(self.decisions, name), "is_shown")
                self.assertIn("sr_has_space_program = yes", shown)
                self.assertIn(f"modifier:{bool_of(base)} = yes", shown)
                self.assertRegex(shown, r"NOT\s*=\s*\{\s*modifier:" + bool_of(pm) + r"\s*=\s*yes\s*\}")

    def test_mission_needs_the_rank_every_milestone_needs(self):
        for name in MISSIONS:
            with self.subTest(decision=name):
                possible = block(block(self.decisions, name), "possible")
                self.assertRegex(possible, r"text\s*=\s*sr_unlock_rank_tt\s*is_great_or_major_power\s*=\s*yes")

    def test_decision_waits_for_its_milestones_prerequisites(self):
        # Everything the target's milestones need beyond what the target
        # itself serves must be complete, or the switch buys nothing.
        for name, (pm, _) in MISSIONS.items():
            with self.subTest(decision=name):
                served = self.served(pm)
                needed = set().union(*(self.milestones[m][0] for m in served)) - served
                have = positive_completions(block(block(self.decisions, name), "possible"))
                self.assertTrue(needed <= self.closure(have), f"{needed - self.closure(have)} missing")

    def test_owner_rule_current_missions_milestones_complete(self):
        for name in OWNER_RULE:
            pm, base = MISSIONS[name]
            with self.subTest(decision=name):
                have = positive_completions(block(block(self.decisions, name), "possible"))
                self.assertTrue(self.served(base) <= self.closure(have))

    def test_interstellar_waits_for_the_probes_own_prerequisites_only(self):
        have = positive_completions(block(block(self.decisions, "te_decision_space_mission_interstellar"), "possible"))
        self.assertEqual(have, self.milestones["interstellar_probe"][0])

    def test_units_match_the_methods_launch_capacity(self):
        for pm, value in UNITS_VALUE.items():
            with self.subTest(pm=pm):
                pm_units = re.search(r"goods_input_launch_capacity_add\s*=\s*(\d+)", block(self.pms, pm)).group(1)
                sv_units = re.search(r"^" + value + r"\s*=\s*(\d+)", self.values, re.M).group(1)
                self.assertEqual(pm_units, sv_units)

    def test_ai_weighs_the_increase_and_races_only_when_it_counts(self):
        for name in [*MISSIONS, "te_decision_found_space_program"]:
            with self.subTest(decision=name):
                ai = block(block(self.decisions, name), "ai_chance")
                self.assertIn("sr_ai_should_participate = yes", ai)
                self.assertIn("in_default = no", ai)
                self.assertRegex(ai, r"net_fixed_income > sr_mission_bill_\w+")
        for name in MISSIONS:
            body = block(self.values, "sr_mission_bill_increase_" + name.rsplit("space_mission_", 1)[1])
            self.assertIn("subtract = sr_mission_units_current", body)

    def test_pm_group_is_most_productive(self):
        pmg = block(strip_comments(read(PMGS)), "REPLACE_OR_CREATE:pmg_base_building_space_program")
        self.assertIn("ai_selection = most_productive", pmg)

    def test_found_builds_in_a_market_capital_we_lead(self):
        body = block(self.decisions, "te_decision_found_space_program")
        self.assertIn("market_capital ?= { owner = ROOT }", block(body, "possible"))
        self.assertIn("has_technology_researched = guided_missiles", block(body, "possible"))
        when = block(body, "when_taken")
        self.assertRegex(when, r"market_capital\s*=\s*\{\s*create_building")
        self.assertIn("building = building_space_program", when)
        self.assertRegex(when, r"activate_production_methods\s*=\s*\{\s*pm_earth_orbit\s*\}")
        building = block(strip_comments(read(BUILDINGS)), "REPLACE_OR_CREATE:building_space_program")
        self.assertIn("owner.market_capital ?= THIS", block(building, "possible"))
        self.assertIn("guided_missiles", block(building, "unlocking_technologies"))


class StrategicReserveDecisionTest(unittest.TestCase):
    def test_hub_is_placed_under_the_relocation_guard(self):
        body = block(strip_comments(read(DECISIONS)), "te_decision_establish_strategic_reserve")
        shown = block(body, "is_shown")
        self.assertIn("has_technology_researched = logistics", shown)
        # Rebels mid-war found no reserve: their zero stock would beat the
        # loser's in the variable merge if they won.
        self.assertIn("is_revolutionary = no", shown)
        self.assertRegex(shown, r"NOT\s*=\s*\{\s*any_scope_building\s*=\s*\{\s*is_building_type\s*=\s*building_strategic_reserve_hub")
        self.assertIn("exists = capital", block(body, "possible"))
        when = block(body, "when_taken")
        raise_at = when.index("set_variable = { name = st_res_hub_relocating value = 1 }")
        create_at = when.index("building = building_strategic_reserve_hub")
        remove_at = when.index("remove_variable = st_res_hub_relocating")
        self.assertLess(raise_at, create_at)
        self.assertLess(create_at, remove_at)
        self.assertRegex(when, r"capital\s*=\s*\{\s*create_building")
        # The hub's one-per-country guard accepts the guard variable.
        hub_possible = block(block(strip_comments(read(HUB)), "building_strategic_reserve_hub"), "possible")
        self.assertIn("owner = { has_variable = st_res_hub_relocating }", hub_possible)

    def test_ai_mirrors_the_hubs_ai_value(self):
        ai = block(block(strip_comments(read(DECISIONS)), "te_decision_establish_strategic_reserve"), "ai_chance")
        self.assertIn("is_great_or_major_power = yes", ai)
        self.assertIn("is_at_war = no", ai)
        self.assertIn("gdp > st_res_ai_hub_min_gdp", ai)


class LocalizationTest(unittest.TestCase):
    def test_every_decision_and_tooltip_has_loc(self):
        text = strip_comments(read(DECISIONS))
        keys = loc_keys()
        names = re.findall(r"^(te_decision_\w+)\s*=\s*\{", text, re.M)
        # Establish a Strategic Reserve, the six space decisions and
        # Restructure the Public Debt (#800).
        self.assertEqual(len(names), 8)
        for name in names:
            for key in (name, f"{name}_desc"):
                with self.subTest(key=key):
                    self.assertIn(key, keys)
        for key in set(re.findall(r"text\s*=\s*(te_decision_tt_\w+)", text)):
            with self.subTest(key=key):
                self.assertIn(key, keys)

    def test_tooltip_bills_match_the_units(self):
        # The "When taken" lines print each mission's weekly Launch Capacity;
        # they are copies of sr_mission_units_*, which the methods pin.
        values = strip_comments(read(VALUES))
        tooltips = {
            "te_decision_tt_create_space_program": "sr_mission_units_earth_orbit",
            "te_decision_tt_begin_moon_mission": "sr_mission_units_moon",
            "te_decision_tt_begin_mars_mission": "sr_mission_units_mars",
            "te_decision_tt_begin_solar_mission": "sr_mission_units_solar",
            "te_decision_tt_begin_deep_space_mission": "sr_mission_units_deep_space",
            "te_decision_tt_begin_interstellar_mission": "sr_mission_units_interstellar",
        }
        units = {}
        for key, value in tooltips.items():
            with self.subTest(key=key):
                shown = re.search(r"buys ([\d,]+) \$launch_capacity\$ a week", loc_value(key))
                self.assertIsNotNone(shown, key)
                units[value] = int(re.search(r"^" + value + r"\s*=\s*(\d+)", values, re.M).group(1))
                self.assertEqual(int(shown.group(1).replace(",", "")), units[value])
        # "three times the Launch Capacity" in the Moon Mission's description.
        self.assertIn("three times the $launch_capacity$", loc_value("te_decision_space_mission_moon_desc"))
        self.assertEqual(units["sr_mission_units_moon"], 3 * units["sr_mission_units_earth_orbit"])


if __name__ == "__main__":
    unittest.main()
