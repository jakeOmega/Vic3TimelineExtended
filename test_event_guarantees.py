"""`scripts/analysis/event_guarantees.py`: what a trigger guarantees about technology,
and what the gates outside the trigger add (#1622)."""
import contextlib
import io
import json
import os
import tempfile
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


# ---------------------------------------------------------------------------
# The gates outside the trigger (#1622), each on a small tree of its own
# ---------------------------------------------------------------------------

TECHS = """
old_tech = { era = era_1 }
mid_tech = { era = era_5 unlocking_technologies = { old_tech } }
late_tech = { era = era_9 unlocking_technologies = { mid_tech } }
other_late = { era = era_9 unlocking_technologies = { mid_tech } }
side_tech = { era = era_6 }
"""


class Tree:
    """A throwaway mod tree: `Tree({"events/x.txt": "..."})`, with TECHS as its technologies."""

    def __init__(self, files: dict):
        self._dir = tempfile.TemporaryDirectory()
        self.root = self._dir.name
        for rel, text in {"common/technology/technologies/t.txt": TECHS, **files}.items():
            path = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        self.script = eg.Script(self.root)

    def analyze(self, event_id: str) -> dict:
        (event,) = eg.find_events(event_id, self.root)
        return eg.analyze(*event, self.script)

    def text(self, event_id: str) -> str:
        return eg.render_event(self.analyze(event_id), self.script)

    def close(self):
        self._dir.cleanup()


class GateTests(unittest.TestCase):
    """Gate is the whole rule: together adds up, one-of keeps what both have."""

    def test_both_and_either(self):
        a = eg.Gate(frozenset({"x", "shared"}), 9, frozenset({"gone"}), ("s", "t"))
        b = eg.Gate(frozenset({"y", "shared"}), 6, frozenset(), ("t",))
        both = a.both(b)
        self.assertEqual((both.techs, both.era), (frozenset({"x", "y", "shared"}), 9))
        either = a.either(b)
        self.assertEqual((either.techs, either.era, either.absent, either.statements),
                         (frozenset({"shared"}), 6, frozenset(), ("t",)))
        self.assertEqual(a.either(eg.NOTHING), eg.NOTHING)
        self.assertFalse(eg.NOTHING)


class FixtureCase(unittest.TestCase):
    FILES: dict = {}

    @classmethod
    def setUpClass(cls):
        cls.tree = Tree(cls.FILES)
        cls.addClassCleanup(cls.tree.close)

    def guaranteed(self, event_id: str) -> set:
        return set(self.tree.analyze(event_id)["guaranteed"]["technologies"])


class LawTests(FixtureCase):
    FILES = {
        "common/laws/l.txt": """
law_new = {
	unlocking_technologies = { late_tech }
	unlocking_laws = { law_b }
}
law_b = { unlocking_technologies = { side_tech } }
law_c = { unlocking_technologies = { side_tech other_late } }
law_free = { }
""",
        "common/laws/m.txt": "INJECT:law_new = {\n\tunlocking_laws = { law_c }\n}\n",
        "common/on_actions/o.txt": "on_law_checkpoint_debate = {\n\trandom_events = {\n\t\t10 = fx.1\n\t\t10 = fx.2\n\t\t10 = fx.3\n\t\t10 = fx.4\n\t}\n}\n",
        "events/fx.txt": """namespace = fx
fx.1 = {
	trigger = { is_enacting_law = law_type:law_new }
}
fx.2 = {
	trigger = {
		OR = {
			is_enacting_law = law_type:law_new
			is_enacting_law = law_type:law_c
		}
	}
}
fx.3 = {
	trigger = { has_law = law_type:law_b }
}
fx.4 = {
	trigger = { is_enacting_law = law_type:law_free }
}
""",
    }

    def test_a_law_being_enacted_brings_its_unlocking_technologies_and_laws(self):
        data = self.tree.analyze("fx.1")
        self.assertEqual(data["trigger"]["required"], [])  # nothing in the trigger names a technology
        (source,) = data["trigger"]["sources"]
        self.assertEqual(source["label"], "law law_new unlocks at")
        self.assertEqual(source["technologies"], ["late_tech"])
        self.assertEqual(source["laws"], ["law_b", "law_c"])  # the INJECTed list adds to the law's own
        # late_tech and its prerequisites; side_tech, which both unlocking laws need; not
        # other_late, which only one of them does.
        self.assertEqual(self.guaranteed("fx.1"), {"late_tech", "mid_tech", "old_tech", "side_tech"})
        self.assertEqual(data["guaranteed"]["assume_through_era"], 6)
        text = self.tree.text("fx.1")
        self.assertIn("law law_new unlocks at: late_tech (era 9); one of the laws law_b, law_c", text)
        self.assertIn("each of those laws needs side_tech (era 6)", text)

    def test_one_of_several_laws_guarantees_what_they_share(self):
        data = self.tree.analyze("fx.2")
        # law_new needs late_tech, law_c other_late: neither is sure, their shared prerequisites
        # and side_tech are, and both are era 9.
        self.assertEqual(self.guaranteed("fx.2"), {"mid_tech", "old_tech", "side_tech"})
        self.assertEqual(data["guaranteed"]["era"], 9)
        self.assertIn("a technology of era 9 or later; every technology of era 6 or earlier", self.tree.text("fx.2"))

    def test_a_law_in_force_is_read_the_same_and_says_what_it_assumes(self):
        text = self.tree.text("fx.3")
        self.assertIn("law law_b (in force) unlocks at: side_tech (era 6)", text)
        self.assertIn("unless the country began the game with the law", text)
        self.assertEqual(self.guaranteed("fx.3"), {"side_tech"})

    def test_a_law_with_no_unlock_guarantees_nothing(self):
        self.assertIn("law law_free unlocks at: no technology", self.tree.text("fx.4"))
        self.assertEqual(self.guaranteed("fx.4"), set())


class ScriptedTriggerTests(FixtureCase):
    FILES = {
        "common/scripted_triggers/t.txt": """
has_late = {
	OR = {
		has_technology_researched = late_tech
		has_technology_researched = other_late
	}
}
outer = { inner = yes }
inner = { has_technology_researched = side_tech }
takes = { has_technology_researched = $TECH$ }
""",
        "common/on_actions/o.txt": "on_monthly_pulse_country = {\n\trandom_events = {\n\t\t1 = fx.1\n\t\t1 = fx.2\n\t\t1 = fx.3\n\t}\n}\n",
        "events/fx.txt": """namespace = fx
fx.1 = {
	trigger = { has_late = yes }
}
fx.2 = {
	trigger = { outer = yes }
}
fx.3 = {
	trigger = { takes = { TECH = side_tech } }
	desc = {
		first_valid = {
			triggered_desc = {
				trigger = { has_late = yes }
				desc = fx.3.d_late
			}
			triggered_desc = { desc = fx.3.d }
		}
	}
}
""",
    }

    def test_a_scripted_trigger_is_opened_one_level(self):
        data = self.tree.analyze("fx.1")
        (source,) = data["trigger"]["sources"]
        self.assertEqual(source["label"], "scripted trigger has_late tests")
        self.assertEqual(source["text"], "one of late_tech (era 9), other_late (era 9)")
        # Either technology: neither is sure, what both require is, and so is era 9.
        self.assertEqual(self.guaranteed("fx.1"), {"mid_tech", "old_tech"})
        self.assertEqual(data["guaranteed"]["assume_through_era"], 6)

    def test_only_one_level(self):
        data = self.tree.analyze("fx.2")
        self.assertEqual([s["text"] for s in data["trigger"]["sources"]], ["inner = yes"])
        self.assertEqual(self.guaranteed("fx.2"), set())

    def test_arguments_are_filled_in(self):
        self.assertEqual(self.guaranteed("fx.3"), {"side_tech"})

    def test_a_text_with_a_test_of_its_own_is_listed(self):
        (variant,) = self.tree.analyze("fx.3")["variants"]
        self.assertEqual((variant["part"], variant["key"]), ("desc", "fx.3.d_late"))
        self.assertEqual(variant["assume_through_era"], 6)
        self.assertIn("only for fx.3.d_late (desc): has_late = yes", self.tree.text("fx.3"))


class JournalEntryTests(FixtureCase):
    FILES = {
        "common/journal_entries/je.txt": """
je_test = {
	is_shown_when_inactive = { has_game_rule = test_rule }
	possible = {
		has_technology_researched = late_tech
		NOT = { has_technology_researched = side_tech }
	}
	on_monthly_pulse = {
		random_events = {
			100 = 0
			10 = fx.1
		}
		effect = {
			random_country = {
				limit = { has_technology_researched = side_tech }
				trigger_event = { id = fx.3 }
			}
		}
	}
	outcome = {
		trigger = { has_law = law_type:law_done }
		effect = {
			trigger_event = {
				id = fx.2
				days = 1
			}
		}
	}
}
je_netted = {
	possible = { has_technology_researched = late_tech }
	on_weekly_pulse = { events = { fx.4 } }
}
je_guarded = {
	possible = { has_technology_researched = late_tech }
	on_weekly_pulse = { events = { fx.5 } }
}
INJECT:je_vanilla = {
	on_monthly_pulse = { random_events = { 1 = fx.6 } }
}
je_shared = {
	possible = { has_technology_researched = late_tech }
	effect_all_involved = { trigger_event = { id = fx.8 } }
}
""",
        "common/scripted_effects/e.txt": """
net_effect = {
	add_journal_entry = { type = je_netted }
	if = {
		limit = { has_technology_researched = other_late }
		add_journal_entry = { type = je_guarded }
	}
}
""",
        "vanilla_parsed/common/journal_entries.json": json.dumps({
            "je_vanilla": ["=", {"possible": ["=", {"has_technology_researched": ["=", "side_tech"]}]}],
        }),
        "events/fx.txt": """namespace = fx
fx.1 = { }
fx.2 = { }
fx.3 = { }
fx.4 = { }
fx.5 = { }
fx.6 = { }
fx.7 = {
	trigger = { has_journal_entry = je_test }
}
fx.8 = { }
""",
    }

    def test_an_entry_s_pool_brings_its_possible(self):
        data = self.tree.analyze("fx.1")
        (route,) = data["routes"]
        self.assertEqual((route["kind"], route["name"], route["followed"]), ("journal_entry", "je_test", True))
        labels = {line["label"]: line["text"] for line in route["lines"]}
        self.assertIn("has_game_rule = test_rule", labels["journal entry je_test requires"])
        self.assertIn("late_tech (era 9)", labels["journal entry je_test requires"])
        self.assertEqual(self.guaranteed("fx.1"), {"late_tech", "mid_tech", "old_tech"})
        # Read when the entry activated: the technology it had not researched may be there now.
        self.assertEqual(data["guaranteed"]["absent"], [])
        self.assertIn("in all:        late_tech (era 9) and what they require; every technology of era 6 or earlier",
                      self.tree.text("fx.1"))

    def test_an_outcome_s_event_also_has_the_outcome_s_trigger(self):
        (route,) = self.tree.analyze("fx.2")["routes"]
        tests = [line["text"] for line in route["lines"] if line["label"] == "tests at the dispatch"]
        self.assertEqual(tests, ["has_law = law_type:law_done"])
        self.assertEqual(self.guaranteed("fx.2"), {"late_tech", "mid_tech", "old_tech"})

    def test_an_event_fired_into_another_scope_keeps_only_the_tests_made_there(self):
        (route,) = self.tree.analyze("fx.3")["routes"]
        self.assertEqual(route["kind"], "scope")
        self.assertIn("fires it in another scope (random_country)", route["head"])
        self.assertEqual(self.guaranteed("fx.3"), {"side_tech"})  # the limit of the scope change, not the entry's late_tech

    def test_a_hook_that_runs_for_every_involved_country_is_another_scope(self):
        (route,) = self.tree.analyze("fx.8")["routes"]
        self.assertEqual(route["kind"], "scope")  # the entry's `possible` was the activating country's
        self.assertEqual(self.guaranteed("fx.8"), set())

    def test_an_entry_an_effect_adds_skips_its_possible(self):
        (route,) = self.tree.analyze("fx.4")["routes"]
        added = [line["text"] for line in route["lines"] if line["label"] == "also added by effect"]
        self.assertEqual(added, ["common/scripted_effects/e.txt:3, which skips both: no test the tool can read"])
        self.assertEqual(self.guaranteed("fx.4"), set())
        # An add behind a test gives what the test and the entry's own gate share.
        self.assertEqual(self.guaranteed("fx.5"), {"mid_tech", "old_tech"})

    def test_an_injected_vanilla_entry_is_read_from_the_snapshot(self):
        self.assertEqual(self.guaranteed("fx.6"), {"side_tech"})

    def test_has_journal_entry_in_the_trigger_is_read_too(self):
        data = self.tree.analyze("fx.7")
        self.assertEqual(data["trigger"]["sources"][0]["label"], "journal entry je_test requires")
        self.assertEqual(self.guaranteed("fx.7"), {"late_tech", "mid_tech", "old_tech"})


class PoolTests(FixtureCase):
    FILES = {
        "common/journal_entries/je.txt": "je_pool = {\n\ton_monthly_pulse = {\n\t\teffect = {\n\t\t\tpool_effect = yes\n\t\t}\n\t}\n}\n",
        "common/scripted_effects/e.txt": """
pool_effect = {
	if = {
		limit = { NOT = { has_variable = cooldown } }
		random_list = {
			100 = { }
			0 = {
				trigger = { is_market = yes }
				modifier = {
					if = {
						limit = { has_technology_researched = late_tech is_boom = yes }
						add = 5
					}
					if = {
						limit = { has_technology_researched = late_tech is_frenzy = yes }
						add = 3
					}
				}
				trigger_event = { id = fx.1 }
			}
			0 = {
				modifier = {
					if = {
						limit = { has_technology_researched = late_tech is_boom = yes }
						add = 3
					}
					if = {
						limit = { has_law = law_type:law_loose }
						add = 2
					}
				}
				if = {
					limit = { has_law = law_type:law_planned }
					trigger_event = { id = fx.3 }
				}
				else = {
					trigger_event = { id = fx.2 }
				}
			}
			5 = {
				modifier = {
					if = {
						limit = { has_technology_researched = late_tech }
						add = 5
					}
				}
				trigger_event = { id = fx.4 }
			}
			0 = {
				modifier = {
					add = 1
					multiply = 2
				}
				trigger_event = { id = fx.5 }
			}
		}
	}
}
""",
        "events/fx.txt": "namespace = fx\nfx.1 = { }\nfx.2 = { }\nfx.3 = { }\nfx.4 = { }\nfx.5 = { }\n",
    }

    def lines(self, event_id: str) -> dict:
        (route,) = self.tree.analyze(event_id)["routes"]
        self.assertEqual((route["kind"], route["name"]), ("journal_entry", "je_pool"))
        return {line["label"]: line["text"] for line in route["lines"]}

    def test_a_weight_of_zero_makes_the_modifier_s_tests_requirements(self):
        lines = self.lines("fx.1")
        self.assertEqual(lines["pool weight tests"],
                         "one of [ late_tech (era 9); is_boom = yes ] or [ late_tech (era 9); is_frenzy = yes ]")
        self.assertEqual(lines["tests at the dispatch"], "NOT = { has_variable = cooldown }; is_market = yes")
        self.assertNotIn("! weight added outside that gate", lines)
        self.assertEqual(self.guaranteed("fx.1"), {"late_tech", "mid_tech", "old_tech"})

    def test_weight_added_outside_the_gate_is_flagged_and_guarantees_nothing(self):
        # The shape #1612 reported three times: +2 for a law, beside the technology's gate.
        lines = self.lines("fx.2")
        self.assertEqual(lines["! weight added outside that gate"],
                         "+2 on line 29 does not test late_tech: has_law = law_type:law_loose")
        self.assertEqual(self.guaranteed("fx.2"), set())
        # The branch the event sits in: its `if` failed.
        self.assertIn("NOT = { has_law = law_type:law_planned }", lines["tests at the dispatch"])
        self.assertIn("has_law = law_type:law_planned", self.lines("fx.3")["tests at the dispatch"])

    def test_a_weight_above_zero_takes_nothing_from_the_modifier(self):
        self.assertNotIn("pool weight tests", self.lines("fx.4"))
        self.assertEqual(self.guaranteed("fx.4"), set())

    def test_a_modifier_the_tool_cannot_read_gives_nothing(self):
        self.assertIn("multiply, which the tool does not read", self.lines("fx.5")["pool weight"])
        self.assertEqual(self.guaranteed("fx.5"), set())


class RouteTests(FixtureCase):
    FILES = {
        "common/journal_entries/je.txt": """
je_late = {
	possible = { has_technology_researched = late_tech }
	on_monthly_pulse = {
		random_events = { 1 = fx.1 1 = fx.2 1 = fx.4 }
		effect = { fire_helper = { EVENT = fx.8 TECH = side_tech } }
	}
}
""",
        "common/on_actions/o.txt": """
on_yearly_pulse_country = {
	effect = {
		if = {
			limit = { has_technology_researched = other_late }
			shared_effect = yes
		}
	}
}
custom_on_action = {
	trigger = { has_technology_researched = side_tech }
	events = { fx.6 }
}
on_monthly_pulse_country = {
	on_actions = { custom_on_action }
}
""",
        "common/scripted_effects/e.txt": """
shared_effect = {
	trigger_event = { id = fx.2 }
}
orphan_effect = {
	trigger_event = { id = fx.7 }
}
fire_helper = {
	if = {
		limit = { has_technology_researched = $TECH$ }
		trigger_event = { id = $EVENT$ }
	}
}
""",
        "common/decisions/d.txt": """
decide = {
	possible = { has_technology_researched = late_tech }
	when_taken = { trigger_event = { id = fx.4 } }
}
""",
        "events/fx.txt": """namespace = fx
fx.1 = {
	trigger = { has_technology_researched = late_tech }
	option = {
		name = fx.1.a
		trigger_event = { id = fx.3 }
		scope:target = { trigger_event = { id = fx.5 } }
		if = {
			limit = { has_technology_researched = side_tech }
			trigger_event = { id = fx.9 }
		}
	}
}
fx.2 = {
	trigger = { has_technology_researched = side_tech }
}
fx.3 = { }
fx.4 = { }
fx.5 = { }
fx.6 = { }
fx.7 = { }
fx.8 = { }
fx.9 = {
	option = {
		name = fx.9.a
		trigger_event = { id = fx.9 days = 30 }
	}
}
fx.10 = { }
""",
    }

    def test_two_routes_guarantee_only_what_both_give(self):
        data = self.tree.analyze("fx.2")
        kinds = sorted(route["kind"] for route in data["routes"])
        self.assertEqual(kinds, ["journal_entry", "on_action"])
        by_kind = {route["kind"]: set(route["technologies"]) for route in data["routes"]}
        self.assertEqual(by_kind["journal_entry"], {"late_tech", "mid_tech", "old_tech"})
        self.assertEqual(by_kind["on_action"], {"other_late", "mid_tech", "old_tech"})
        # Not the union: neither era 9 technology is sure. What both need is, and era 9 itself.
        self.assertEqual(set(data["outside"]["technologies"]), {"mid_tech", "old_tech"})
        self.assertEqual(data["outside"]["era"], 9)
        # ... and the event's own trigger on top.
        self.assertEqual(self.guaranteed("fx.2"), {"mid_tech", "old_tech", "side_tech"})
        text = self.tree.text("fx.2")
        self.assertIn("through scripted effect shared_effect", text)
        self.assertIn("tests where shared_effect is called: other_late (era 9)", text)
        self.assertIn("from outside:  all 2 routes give mid_tech (era 5) and what they require; "
                      "a technology of era 9 or later; every technology of era 6 or earlier", text)

    def test_a_sender_is_named_and_none_of_its_technology_carries_over(self):
        data = self.tree.analyze("fx.3")
        (route,) = data["routes"]
        self.assertEqual((route["kind"], route["name"], route["followed"]), ("event", "fx.1", True))
        self.assertIn("sent by: fx.1 (events/fx.txt:6): nothing of the sender's own technology carries over",
                      self.tree.text("fx.3"))
        self.assertEqual(self.guaranteed("fx.3"), set())  # fx.1 needs late_tech; fx.3 is promised none of it
        (route,) = self.tree.analyze("fx.5")["routes"]
        self.assertIn(", into scope:target", route["head"])

    def test_a_test_at_the_send_is_the_receiver_s(self):
        data = self.tree.analyze("fx.9")
        kinds = sorted(route["kind"] for route in data["routes"])
        self.assertEqual(kinds, ["event", "repeat"])  # fx.9 also sends itself again
        self.assertEqual(self.guaranteed("fx.9"), {"side_tech"})
        self.assertIn("sent by: itself", self.tree.text("fx.9"))

    def test_a_route_the_tool_does_not_open_leaves_nothing_from_outside(self):
        data = self.tree.analyze("fx.4")
        followed = {route["kind"]: route["followed"] for route in data["routes"]}
        self.assertEqual(followed, {"journal_entry": True, "not_followed": False})
        # The entry gives late_tech and so does the decision's `possible`, which the tool does
        # not read: one route unread, nothing promised.
        self.assertEqual(data["outside"]["technologies"], [])
        self.assertEqual(len(data["outside"]["not_followed"]), 1)
        self.assertEqual(self.guaranteed("fx.4"), set())
        text = self.tree.text("fx.4")
        self.assertIn("not followed: decision decide (common/decisions/d.txt:4): the tool does not open a decision", text)
        self.assertIn("from outside:  nothing is guaranteed: 1 of 2 route(s) not followed", text)
        self.assertIn("in all:        no technology: assume none", text)

    def test_an_effect_nothing_calls_and_an_event_nothing_fires(self):
        data = self.tree.analyze("fx.7")
        self.assertEqual([route["followed"] for route in data["routes"]], [False])
        self.assertIn("nothing the tool can find calls scripted effect orphan_effect", data["routes"][0]["head"])
        text = self.tree.text("fx.10")
        self.assertIn("fired by:      nothing the tool can find", text)
        self.assertIn("from outside:  nothing is guaranteed", text)

    def test_an_on_action_s_own_trigger_counts(self):
        data = self.tree.analyze("fx.6")
        (route,) = data["routes"]
        labels = {line["label"]: line["text"] for line in route["lines"]}
        self.assertEqual(labels["on-action custom_on_action requires"], "side_tech (era 6)")
        self.assertIn("on_monthly_pulse_country", labels["called from"])
        self.assertEqual(self.guaranteed("fx.6"), {"side_tech"})

    def test_an_effect_handed_the_event_is_read_with_its_arguments(self):
        data = self.tree.analyze("fx.8")
        (route,) = data["routes"]
        self.assertEqual(route["kind"], "journal_entry")
        self.assertEqual(self.guaranteed("fx.8"), {"late_tech", "mid_tech", "old_tech", "side_tech"})


class OwnTriggerOnlyTests(unittest.TestCase):
    def test_without_a_script_nothing_outside_is_read(self):
        body = "{\n\ttrigger = { is_enacting_law = law_type:law_command_economy has_technology_researched = radio }\n}"
        text = eg.describe("x.1", "events/x.txt", body, eg.load_technologies())
        self.assertIn("requires:      radio (era", text)
        self.assertNotIn("unlocks at", text)
        self.assertNotIn("fired by", text)


class DocCheckTests(FixtureCase):
    FILES = {
        "common/on_actions/o.txt": "on_monthly_pulse_country = {\n\trandom_events = {\n\t\t1 = fx.1\n\t}\n}\n",
        "events/fx.txt": "namespace = fx\nfx.1 = {\n\ttrigger = { has_technology_researched = late_tech }\n}\n",
    }
    DOC = """
| Where | Guaranteed | Not guaranteed |
|---|---|---|
| `fx` (.1 from the monthly pool) | `late_tech` (era 9) and `old_tech`, which it brings | `side_tech` |
| `fx.1` again | `other_late` (era 5), and `side_tech`, three eras behind | Nothing |
| `no_such_chain` | `other_late` | Nothing |
"""

    def test_a_row_is_held_to_what_the_tool_finds(self):
        def analyses(namespace):
            return [self.tree.analyze("fx.1")] if namespace == "fx" else []

        findings = eg.check_doc(self.DOC, self.tree.script, analyses)
        self.assertEqual(len(findings), 2, findings)
        self.assertIn("line 5: `other_late` is given as era 5; it is era 9", findings[0])
        self.assertIn("line 5: fx: the row guarantees `other_late` (era 9)", findings[1])


class RepoTests(unittest.TestCase):
    """The gates the issue names, on the mod's own script."""

    @classmethod
    def setUpClass(cls):
        cls.script = eg.Script()

    def analyze(self, event_id: str) -> dict:
        (event,) = eg.find_events(event_id)
        return eg.analyze(*event, self.script)

    def test_an_enactment_event_cannot_fire_before_its_laws_unlock(self):
        data = self.analyze("extra_law_events.5")  # three privacy laws, each behind an era 9 technology
        self.assertEqual(data["trigger"]["required"], [])
        self.assertEqual(data["guaranteed"]["era"], 9)
        self.assertEqual(data["guaranteed"]["assume_through_era"], 6)

    def test_an_entry_s_events_inherit_its_gate(self):
        self.assertIn("combined_arms", self.analyze("world_war_events.2")["guaranteed"]["technologies"])
        data = self.analyze("augmentation_events.1")  # has_augmentation_tech: either era 11 technology
        self.assertIn("brain_computer_interfaces", data["guaranteed"]["technologies"])
        self.assertEqual(data["guaranteed"]["assume_through_era"], 8)

    def test_a_banking_draw_has_its_pool_s_technology(self):
        data = self.analyze("banking_cycle_events.5")
        self.assertFalse(data["trigger"]["present"])
        self.assertIn("railways", data["guaranteed"]["technologies"])

    def test_json_and_trigger_from_the_command_line(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(eg.main(["augmentation_events.1", "--json"]), 0)
        (data,) = json.loads(out.getvalue())
        self.assertEqual(data["event"], "augmentation_events.1")
        self.assertEqual(data["routes"][0]["kind"], "journal_entry")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(eg.main(["--trigger", "has_augmentation_tech"]), 0)
        self.assertIn("scripted trigger has_augmentation_tech tests: one of", out.getvalue())


if __name__ == "__main__":
    unittest.main()
