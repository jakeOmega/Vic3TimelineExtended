"""Climate policies that need something a country must be able to build are gated on its technology.

Renewable Investment boosts and subsidises Renewable Energy Plants, so it waits
for the technology that unlocks them; Emission Standards, Public Transit, Green
Building Codes and Carbon Removal Support likewise (see the header of
common/scripted_triggers/global_warming_triggers.txt). Fiscal and administrative
policies stay ungated.

The engine raises nothing if a gate drifts from what it is meant to track (a
renamed technology, a building moved to another one), and treaty 109 forces
seven of the policies on its source, so it must only bind a source that could
carry them out. This checks each gate, the reason it exists, the treaty's list
against the gates of the policies it forces, and that the Environmental
Movement and the AI's buttons read the same adoption tests.
"""

import re
import unittest

from test_tax_code_rule import ROOT, load

TRIGGERS = "common/scripted_triggers/global_warming_triggers.txt"
TREATY = "common/treaty_articles/109_enforce_emissions_reduction.txt"
BUTTONS = "common/scripted_buttons/global_warming_buttons.txt"
MOVEMENTS = "common/political_movements/new_ideological_movements.txt"

# policy -> technology its adoption needs (None: no gate).
GATES = {
    "carbon_tax": None,
    "renewable_investment": "clean_energy_technologies",
    "climate_adaptation": None,
    "emission_standards": "pollution_control",
    "reforestation": None,
    "public_transit": "modern_urban_planning",
    "fossil_fuel_divestment": None,
    "green_building_codes": "clean_energy_technologies",
    "carbon_removal": "carbon_capture_and_storage",
    "fossil_fuel_tariffs": None,
}

# What each technology is there for: (file, entity, technology it names).
REASONS = (
    ("common/buildings/extra_buildings.txt", "REPLACE_OR_CREATE:building_renewable_energy_plant", "clean_energy_technologies"),
    ("common/buildings/extra_buildings.txt", "REPLACE_OR_CREATE:building_synthetics_plant_coal", "carbon_capture_and_storage"),
    ("common/production_methods/extra_pms.txt", "pm_multimodal_transit", "modern_urban_planning"),
)


def _techs(body):
    value = body.get("has_technology_researched", [])
    return {value} if isinstance(value, str) else set(value)


def _possible_modifier(body):
    """The policy modifier whose absence the adoption test's first line checks."""
    tooltips = body["custom_tooltip"]
    first = tooltips[0] if isinstance(tooltips, list) else tooltips
    # Tariffs test their own trigger (they follow the market leader), not a modifier.
    return first.get("NOT", {}).get("je:je_global_warming", {}).get("has_modifier")


class PolicyTechGates(unittest.TestCase):
    def setUp(self):
        self.triggers = load(TRIGGERS)

    def test_each_policy_needs_exactly_its_technology(self):
        for policy, tech in GATES.items():
            with self.subTest(policy=policy):
                body = self.triggers[f"gw_possible_{policy}"]
                self.assertEqual(_techs(body), {tech} if tech else set())

    def test_repeal_never_needs_a_technology(self):
        for policy in GATES:
            with self.subTest(policy=policy):
                self.assertEqual(_techs(self.triggers[f"gw_possible_remove_{policy}"]), set())

    def test_each_technology_still_unlocks_what_the_policy_relies_on(self):
        for path, entity, tech in REASONS:
            with self.subTest(entity=entity):
                body = load(path)[entity]
                self.assertIn(tech, body["unlocking_technologies"])
        defined = set()
        for path in (ROOT / "common/technology/technologies").glob("*.txt"):
            defined.update(load(path.relative_to(ROOT)))
        for tech in {t for t in GATES.values() if t}:
            self.assertIn(tech, defined)


class EmissionsTreatyTechGate(unittest.TestCase):
    def setUp(self):
        self.triggers = load(TRIGGERS)
        self.article = load(TREATY)["enforce_emissions_reduction"]

    def test_treaty_needs_the_union_of_its_forced_policies_gates(self):
        by_modifier = {}
        for policy in GATES:
            modifier = _possible_modifier(self.triggers[f"gw_possible_{policy}"])
            if modifier:
                by_modifier[modifier] = policy
        text = (ROOT / TREATY).read_text(encoding="utf-8-sig")
        freeze = text[text.index("non_fulfillment"):text.index("\tai = {")]
        forced = set(re.findall(r"has_modifier = (\w+)", freeze))
        self.assertEqual(len(forced), 7)
        expected = set()
        for modifier in forced:
            tech = GATES[by_modifier[modifier]]
            if tech:
                expected.add(tech)
        self.assertEqual(_techs(self.triggers["gw_has_emissions_treaty_technologies"]), expected)

    def test_possible_and_can_ratify_both_check_the_source(self):
        gate = {"text": "gw_treaty_source_has_technologies_tt", "gw_has_emissions_treaty_technologies": "yes"}
        self.assertEqual(self.article["possible"]["custom_tooltip"], gate)
        self.assertIn(
            {"text": "gw_treaty_source_has_technologies_tt", "scope:source_country": {"gw_has_emissions_treaty_technologies": "yes"}},
            self.article["can_ratify"]["custom_tooltip"],
        )


class SameTestEverywhere(unittest.TestCase):
    def test_ai_adopt_buttons_read_the_adoption_test(self):
        buttons = load(BUTTONS)
        for policy in GATES:
            with self.subTest(policy=policy):
                self.assertEqual(buttons[f"gw_{policy}_button"]["possible"], {f"gw_possible_{policy}": "yes"})

    def test_environmental_movement_wants_only_what_the_country_could_adopt(self):
        text = (ROOT / MOVEMENTS).read_text(encoding="utf-8-sig")
        wants = re.findall(r"limit = \{\s*([^{}]*?)\s*\}\s*add = \{ value = 0\.1 desc = \"POLICY_POSSIBLE_(\w+)\"", text)
        self.assertEqual(len(wants), 7)
        for limit, key in wants:
            with self.subTest(policy=key):
                calls = re.findall(r"gw_possible_(\w+) = yes", limit)
                self.assertEqual(len(calls), 1, limit)
                self.assertIn(calls[0], GATES)
                self.assertIn("has_journal_entry = je_global_warming", limit)


if __name__ == "__main__":
    unittest.main()
