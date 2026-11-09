"""`scripts/analysis/event_guarantees.py`: what a trigger guarantees about technology."""
import unittest

import scripts.analysis.event_guarantees as eg


class TechnologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.techs = eg.load_technologies()

    def test_reads_vanilla_and_mod_technologies(self):
        self.assertEqual(self.techs["telephone"]["era"], 4)        # vanilla
        self.assertEqual(self.techs["social_media"]["era"], 9)     # the mod's
        self.assertIn("pop_culture", self.techs["social_media"]["requires"])

    def test_prerequisites_are_recursive_and_stay_in_their_category(self):
        closure = eg.prerequisites("social_media", self.techs)
        self.assertIn("television_broadcasting", closure)
        self.assertIn("academia", closure)
        self.assertNotIn("telephone", closure)  # production: no society tech can require it

    def test_three_eras_back_is_assumed(self):
        closure, cutoff = eg.assumed(["social_media"], self.techs)
        self.assertEqual(cutoff, 6)
        self.assertLessEqual(self.techs["telephone"]["era"], cutoff)
        _, early = eg.assumed(["mass_propaganda"], self.techs)   # era 5
        self.assertEqual(early, 2)
        self.assertGreater(self.techs["radio"]["era"], early)    # radio is not assumed
        self.assertEqual(eg.assumed([], self.techs), (set(), None))


class TriggerTests(unittest.TestCase):
    BODY = """{
	type = country_event
	trigger = {
		in_election_campaign = yes
		has_technology_researched = mass_propaganda
		NOT = { has_technology_researched = television_broadcasting }
		OR = {
			has_technology_researched = radio
			has_technology_researched = film
		}
		any_interest_group = {
			has_party = yes
			has_technology_researched = nested_does_not_count
		}
	}
	option = {
		trigger = { has_technology_researched = option_only }
	}
}"""

    def test_reads_the_event_s_own_trigger(self):
        trigger = eg.read_trigger(self.BODY)
        self.assertEqual(trigger["required"], ["mass_propaganda"])
        self.assertEqual(trigger["absent"], ["television_broadcasting"])
        self.assertEqual(trigger["one_of"], [["radio", "film"]])
        self.assertIn("in_election_campaign = yes", trigger["other"])
        self.assertTrue(any(s.startswith("any_interest_group") for s in trigger["other"]))

    def test_no_trigger(self):
        self.assertFalse(eg.read_trigger("{\n\ttype = country_event\n}")["has_trigger"])

    def test_finds_the_mod_s_events(self):
        one = eg.find_events("modern_election_events.11")
        self.assertEqual([e[0] for e in one], ["modern_election_events.11"])
        chain = eg.find_events("modern_election_events")
        self.assertGreater(len(chain), 30)
        text = eg.describe(*one[0], eg.load_technologies())
        self.assertIn("mass_propaganda (era 5)", text)
        self.assertIn("must NOT have: television_broadcasting", text)


if __name__ == "__main__":
    unittest.main()
