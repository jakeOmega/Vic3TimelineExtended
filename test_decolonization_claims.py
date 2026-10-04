"""Pin the engine scopes used to renounce decentralized colonial claims.

Equateur can be split between Sudan and a decentralized owner. Claims belong
to the region, so both the notification pre-check and the removal filter must
ask the claimer's country about that region, rather than its individual states.
These are script wiring checks; they do not execute the Victoria 3 engine.
"""

from pathlib import Path
import unittest

from paradox_file_parser import ParadoxFileParser


REPO = Path(__file__).resolve().parent
MARKER = "modifier:country_remove_decentralized_claims_bool"


def parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(REPO / path))
    return parser.data


def body(node, key):
    operator, value = node[key]
    if operator != "=":
        raise AssertionError(f"unexpected operator for {key}: {operator}")
    return value


class DecolonizationClaimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actions = parse("common/on_actions/extra_on_actions.txt")
        effect = body(body(cls.actions, "tech_marker_grants_on_action"), "effect")
        cls.sweep = next(value for operator, value in effect["if"]
                         if body(value, "limit").get(MARKER) == ("=", "yes"))

    def test_researched_tech_keeps_running_the_monthly_cleanup(self):
        tech = body(parse("common/technology/technologies/era_6.txt"), "decolonization")
        self.assertEqual(body(body(tech, "modifier"), MARKER.removeprefix("modifier:")), "yes")
        monthly = body(body(self.actions, "on_monthly_pulse_country"), "on_actions")
        self.assertIn("tech_marker_grants_on_action", monthly)
        limit = body(self.sweep, "limit")
        self.assertEqual(limit["number_of_claims"], (">", "0"))
        self.assertNotIn("has_variable", limit)
        self.assertNotIn("set_variable", self.sweep)

    def test_precheck_reads_the_region_claim_from_the_claimer(self):
        countries = body(body(self.sweep, "limit"), "any_decentralized_country")
        states = body(countries, "any_scope_state")
        region = body(states, "state_region")
        self.assertEqual(body(region, "ROOT"), {"has_claim": ("=", "PREV")})

    def test_removal_filter_reads_the_same_region_claim(self):
        countries = body(self.sweep, "every_decentralized_country")
        states = body(countries, "every_scope_state")
        region = body(body(states, "limit"), "state_region")
        self.assertEqual(body(region, "ROOT"), {"has_claim": ("=", "PREV")})
        self.assertEqual(body(states, "state_region"), {"remove_claim": ("=", "ROOT")})

    def test_centralized_only_regions_are_outside_the_sweep(self):
        self.assertNotIn("any_country", body(self.sweep, "limit"))
        self.assertNotIn("every_country", self.sweep)
        self.assertNotIn("every_state_region", self.sweep)
        self.assertIn("every_decentralized_country", self.sweep)

    def test_notification_requires_a_matching_decentralized_region_claim(self):
        self.assertEqual(body(self.sweep, "post_notification"), "decentralized_claims_renounced")
        self.assertIn("any_decentralized_country", body(self.sweep, "limit"))


if __name__ == "__main__":
    unittest.main()
