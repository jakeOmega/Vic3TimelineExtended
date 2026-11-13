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
        self.assertIn("radio (era 4)", text)
        self.assertIn("must NOT have: television (era 6), television_broadcasting (era 7)", text)


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

    def in_play(self, event_id: str) -> set:
        """The further technology that holds only if the laws in force were enacted in play."""
        return set((self.tree.analyze(event_id)["if_enacted_in_play"] or {"technologies": []})["technologies"])


class LawTests(FixtureCase):
    FILES = {
        "common/laws/l.txt": """
law_new = {
	unlocking_technologies = { late_tech }
	unlocking_laws = { law_b }
}
law_b = { unlocking_technologies = { side_tech } }
law_c = { unlocking_technologies = { other_late } unlocking_laws = { law_b } }
law_pair = { unlocking_technologies = { side_tech other_late } }
law_free = { }
law_started = { unlocking_technologies = { late_tech } }
""",
        "common/scripted_effects/e.txt": "grant_effect = {\n\tstart_enactment = law_type:law_started\n}\n",
        "common/laws/m.txt": "INJECT:law_new = {\n\tunlocking_laws = { law_c }\n}\n",
        "common/on_actions/o.txt": "on_law_checkpoint_debate = {\n\trandom_events = {\n\t\t10 = fx.1\n\t\t10 = fx.2\n\t\t10 = fx.3\n\t\t10 = fx.4\n\t\t10 = fx.5\n\t\t10 = fx.6\n\t}\n}\n",
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
fx.5 = {
	trigger = { is_enacting_law = law_type:law_started }
}
fx.6 = {
	trigger = { is_enacting_law = law_type:law_pair }
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
        # late_tech and its prerequisites are sure: the law is being enacted now.
        self.assertEqual(self.guaranteed("fx.1"), {"late_tech", "mid_tech", "old_tech"})
        self.assertEqual(data["guaranteed"]["assume_through_era"], 6)
        # side_tech, which both unlocking laws need, is not: an unlocking law is a law in
        # force, and the country may have begun the game with it. other_late, which only one
        # of them needs, is nowhere.
        self.assertEqual(self.in_play("fx.1"), {"side_tech"})
        text = self.tree.text("fx.1")
        self.assertIn("law law_new unlocks at: late_tech (era 9); one of the laws law_b, law_c", text)
        self.assertIn("each of those laws needs side_tech (era 6)", text)
        self.assertIn("in all:        late_tech (era 9) and what they require; every technology of era 6 or earlier", text)
        self.assertIn("if enacted in play: late_tech (era 9), side_tech (era 6) and what they require", text)

    def test_one_of_several_laws_guarantees_what_they_share(self):
        data = self.tree.analyze("fx.2")
        # law_new needs late_tech, law_c other_late: neither is sure, their shared prerequisites
        # are, and both are era 9. side_tech is behind an unlocking law of each: in play only.
        self.assertEqual(self.guaranteed("fx.2"), {"mid_tech", "old_tech"})
        self.assertEqual(self.in_play("fx.2"), {"side_tech"})
        self.assertEqual(data["guaranteed"]["era"], 9)
        self.assertIn("a technology of era 9 or later; every technology of era 6 or earlier", self.tree.text("fx.2"))

    def test_a_law_in_force_guarantees_no_technology(self):
        # history's activate_law skips the unlocking technology, so a country can begin the
        # game with law_b and no side_tech: the technology is shown, beside the total, not in it.
        data = self.tree.analyze("fx.3")
        self.assertEqual(data["guaranteed"]["technologies"], [])
        self.assertIsNone(data["guaranteed"]["assume_through_era"])
        self.assertNotIn("if_enacted_in_play", data["guaranteed"])
        self.assertEqual(data["if_enacted_in_play"], {"technologies": ["side_tech"], "era": 6, "assume_through_era": 3})
        text = self.tree.text("fx.3")
        self.assertIn("law law_b (in force) unlocks at: side_tech (era 6) (a law in force: counted only under", text)
        self.assertIn("in all:        no technology: assume none", text)
        self.assertIn("if enacted in play: side_tech (era 6); every technology of era 3 or earlier  (NOT guaranteed:", text)

    def test_an_enactment_an_effect_can_start_guarantees_no_technology(self):
        # start_enactment is measured to start an enactment, not to check the technology.
        self.assertEqual(self.guaranteed("fx.5"), set())
        self.assertEqual(self.in_play("fx.5"), {"late_tech", "mid_tech", "old_tech"})
        self.assertIn("an effect starts this law's enactment, common/scripted_effects/e.txt:2", self.tree.text("fx.5"))

    def test_several_unlocking_technologies_guarantee_only_what_each_gives(self):
        # Whether the engine needs all of a law's unlocking technologies or any one is
        # unverified (#1697), so law_pair is read as either: side_tech (era 6) and
        # other_late (era 9) share no technology, and the later era is not sure.
        data = self.tree.analyze("fx.6")
        self.assertEqual(self.guaranteed("fx.6"), set())
        self.assertEqual(data["guaranteed"]["era"], 6)
        (source,) = data["trigger"]["sources"]
        self.assertEqual(source["technologies"], ["side_tech", "other_late"])
        self.assertEqual(source["technologies_needed"], "unverified: all or any one")
        self.assertIn("law law_pair unlocks at: side_tech (era 6) or other_late (era 9) (whether the engine "
                      "needs all of them or any one is unverified", self.tree.text("fx.6"))
        # One technology reads as before, with no such note.
        (one,) = self.tree.analyze("fx.1")["trigger"]["sources"]
        self.assertNotIn("technologies_needed", one)

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
je_twice = {
	possible = { has_technology_researched = late_tech }
}
REPLACE:je_twice = {
	possible = { has_technology_researched = side_tech }
	on_weekly_pulse = { events = { fx.9 } }
}
je_line = {
	possible = { has_technology_researched = late_tech }
	on_monthly_pulse = {
		effect = {
			if = { limit = { has_technology_researched = side_tech } trigger_event = { id = fx.10 } } else = { trigger_event = { id = fx.10 } }
		}
	}
}
je_switches = {
	possible = { has_technology_researched = late_tech }
	on_monthly_pulse = {
		effect = {
			owner = { trigger_event = { id = fx.11 } }
			scope:other = { trigger_event = { id = fx.12 } }
			root = { trigger_event = { id = fx.13 } }
			prev = { trigger_event = { id = fx.14 } }
		}
	}
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
fx.9 = { }
fx.10 = { }
fx.11 = { }
fx.12 = { }
fx.13 = { }
fx.14 = { }
""",
    }

    def test_a_replacing_definition_is_the_entry(self):
        self.assertEqual(self.guaranteed("fx.9"), {"side_tech"})  # not the replaced definition's late_tech as well

    def test_two_dispatches_on_one_line_give_what_both_test(self):
        data = self.tree.analyze("fx.10")
        # The `if` tests side_tech and the `else` on the same line does not: only the entry's gate is sure.
        self.assertEqual(self.guaranteed("fx.10"), {"late_tech", "mid_tech", "old_tech"})
        tests = [line["text"] for route in data["routes"] for line in route["lines"] if line["label"] == "tests at the dispatch"]
        self.assertEqual(tests, ["2 places fire or call it here: only what all of them test is kept"])

    def test_owner_scope_root_and_prev_are_other_scopes(self):
        # The scope rule is event_context_audit's: if its list of same-scope keys ever grew
        # one of these, the entry's technology would be handed to another country's event.
        for key in ("owner", "scope:other", "root", "ROOT", "prev", "PREV", "every_country", "random_country", "c:GBR"):
            self.assertTrue(eg.eca._is_switch(key), key)
        for key in ("if", "else", "random_list", "effect", "option", "immediate", "hidden_effect", "on_monthly_pulse"):
            self.assertFalse(eg.eca._is_switch(key), key)
        for event_id in ("fx.11", "fx.12", "fx.13", "fx.14"):
            (route,) = self.tree.analyze(event_id)["routes"]
            self.assertEqual(route["kind"], "scope", event_id)
            self.assertEqual(self.guaranteed(event_id), set(), event_id)

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


class ParameterAddTests(FixtureCase):
    """`add_journal_entry = { type = je_$M$ }`: the add counts against every entry it could name."""
    FILES = {
        "common/journal_entries/je.txt": """
je_alpha = {
	possible = { has_technology_researched = late_tech }
	on_weekly_pulse = { events = { fx.1 } }
}
je_beta = {
	possible = { has_technology_researched = late_tech }
	on_weekly_pulse = { events = { fx.2 } }
}
other_gamma = {
	possible = { has_technology_researched = late_tech }
	on_weekly_pulse = { events = { fx.3 } }
}
""",
        "common/scripted_effects/e.txt": """
readd = {
	if = {
		limit = { has_technology_researched = side_tech }
		add_journal_entry = { type = je_$M$ }
	}
}
add_unsaid = {
	add_journal_entry = { type = je_b$M$ }
}
add_nothing_known = {
	add_journal_entry = { type = je_missing }
}
""",
        "common/on_actions/o.txt": """
on_yearly_pulse_country = {
	effect = {
		if = {
			limit = { has_technology_researched = other_late }
			readd = { M = alpha }
		}
	}
}
""",
        "events/fx.txt": "namespace = fx\nfx.1 = { }\nfx.2 = { }\nfx.3 = { }\n",
    }

    def added(self, event_id: str) -> list:
        (route,) = self.tree.analyze(event_id)["routes"]
        return [line["text"] for line in route["lines"] if line["label"] == "also added by effect"]

    def test_a_call_that_names_the_entry_is_read_with_the_tests_around_it(self):
        (text,) = self.added("fx.1")
        self.assertEqual(text, "common/scripted_effects/e.txt:5, through readd as called at common/on_actions/o.txt:6, "
                               "which skips both: other_late (era 9); side_tech (era 6)")
        # What the entry's own gate (late_tech) and the add's tests (other_late, side_tech) share.
        self.assertEqual(self.guaranteed("fx.1"), {"mid_tech", "old_tech"})

    def test_an_add_no_call_resolves_counts_for_every_entry_it_fits(self):
        (text,) = self.added("fx.2")
        self.assertIn("`type = je_b$M$`, which the tool cannot resolve", text)
        self.assertEqual(self.guaranteed("fx.2"), set())  # not the late_tech of je_beta's `possible`
        # An entry neither pattern fits keeps its gate.
        self.assertEqual(self.added("fx.3"), [])
        self.assertEqual(self.guaranteed("fx.3"), {"late_tech", "mid_tech", "old_tech"})

    def test_an_add_that_names_no_known_entry_is_reported(self):
        self.tree.analyze("fx.1")
        self.assertEqual(self.tree.script.unknown_adds,
                         ["common/scripted_effects/e.txt:12 adds `je_missing`, which is no journal entry the tool knows"])
        self.assertIn("add_journal_entry: common/scripted_effects/e.txt:12 adds `je_missing`", eg.notes(self.tree.script)[-1])


class BareParameterAddTests(FixtureCase):
    FILES = {
        "common/journal_entries/je.txt": """
je_one = {
	possible = { has_technology_researched = late_tech }
	on_weekly_pulse = { events = { fx.1 } }
}
""",
        "common/scripted_effects/e.txt": "add_it = {\n\tadd_journal_entry = { type = $JE$ }\n}\n",
        "events/fx.txt": "namespace = fx\nfx.1 = { }\n",
    }

    def test_a_bare_parameter_counts_for_every_entry(self):
        self.assertEqual(self.guaranteed("fx.1"), set())
        self.assertIn("`type = $JE$`", self.tree.text("fx.1"))


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
        "common/laws/l.txt": "law_held = { unlocking_technologies = { other_late } }\n",
        "common/on_actions/o.txt": "on_monthly_pulse_country = {\n\trandom_events = {\n\t\t1 = fx.1\n\t\t1 = hx.1\n\t}\n}\n",
        "events/fx.txt": "namespace = fx\nfx.1 = {\n\ttrigger = { has_technology_researched = late_tech }\n}\n",
        "events/hx.txt": "namespace = hx\nhx.1 = {\n\ttrigger = { has_law = law_type:law_held }\n}\n",
    }
    DOC = """
| Where | Guaranteed | Not guaranteed |
|---|---|---|
| `fx` (.1 from the monthly pool) | `late_tech` (era 9) and `old_tech`, which it brings | `side_tech` |
| `fx.1` again | `other_late` (era 5), and `side_tech`, three eras behind | Nothing |
| `no_such_chain` | `other_late` | Nothing |
| `hx.1` under the law | The law is in force (`other_late`) | Nothing |
"""

    def test_a_row_is_held_to_what_the_tool_finds(self):
        def analyses(namespace):
            return [self.tree.analyze(f"{namespace}.1")] if namespace in ("fx", "hx") else []

        findings = eg.check_doc(self.DOC, self.tree.script, analyses)
        self.assertEqual(len(findings), 3, findings)
        self.assertIn("line 5: `other_late` is given as era 5; it is era 9", findings[0])
        self.assertIn("line 5: fx: the row guarantees `other_late` (era 9), which the tool finds guaranteed to none", findings[1])
        # A law in force: the technology is there only if the law was enacted in play.
        self.assertIn("line 7: hx: the row guarantees `other_late` (era 9), which holds only if a law in force was "
                      "enacted in play", findings[2])

    def test_a_where_cell_s_numbers_are_read_past_its_parentheses(self):
        # The list went on past the first parenthesis and was cut there (#1697).
        cases = {
            "`ch` .43–.48, .58": {43, 44, 45, 46, 47, 48, 58},
            "`ch.45` / `.68`": {45, 68},
            "`ch` .8, .9 (milestones, from the pulse) and .19, .20 (fired from .3)": {8, 9, 19, 20},
            "`ch.1` / `.2` (on country formed (BHA only)); `.10` (monthly)": {1, 2, 10},
            "`ch` 25–27 (from .25's `after`), 35 (from .25's options)": {25, 26, 27, 35},
            # Prose after the name: the row is about the whole chain.
            "`ch` (2026-11-12). .1 is fired by .4; .2 at its target": set(),
            "`ch` (2026-11-12). Every event but .1 and .101": set(),
            "`ch`": set(),
        }
        for where, numbers in cases.items():
            with self.subTest(where=where):
                self.assertEqual(eg._row_numbers(where, ["ch"]), numbers)


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
        # World War opens at Combined Arms, or at Trench Works under its early unlock (ww_era_reached), so a text may
        # assume only the earlier.
        self.assertIn("trench_works", self.analyze("world_war_events.2")["guaranteed"]["technologies"])
        data = self.analyze("augmentation_events.1")  # has_augmentation_tech: either era 11 technology
        self.assertIn("brain_computer_interfaces", data["guaranteed"]["technologies"])
        self.assertEqual(data["guaranteed"]["assume_through_era"], 8)

    def test_a_country_that_begins_with_a_law_is_not_promised_its_technology(self):
        # Serbia and Greece begin 1836 with State-Led Language Reform, which unlocks at
        # mass_media (era 6); history's activate_law skips the technology. `.26` needs only
        # the law in force, so a text there may not assume radio-age media.
        with open(os.path.join(eg.REPO_ROOT, "common", "history", "extra_history.txt"), encoding="utf-8-sig") as fh:
            self.assertIn("activate_law = law_type:law_state_led_language_reform", fh.read())
        self.assertEqual(eg.load_laws()["law_state_led_language_reform"]["technologies"], ["mass_media"])
        for event_id in ("extra_law_events.25", "extra_law_events.26", "extra_law_events.27", "extra_law_events.35"):
            data = self.analyze(event_id)
            self.assertNotIn("mass_media", data["guaranteed"]["technologies"], event_id)
            self.assertIsNone(data["guaranteed"]["assume_through_era"], event_id)
            self.assertIn("mass_media", data["if_enacted_in_play"]["technologies"], event_id)

    def test_a_milestone_s_re_entry_add_is_read_through_its_argument(self):
        # je_space_race_$MILESTONE$ is added again after a programme loss; the add is guarded
        # by sr_reentry_due_<m>, which repeats the entry's technology test.
        data = self.analyze("space_race_events.3")
        added = [line["text"] for route in data["routes"] for line in route["lines"]
                 if line["label"] == "also added by effect"]
        self.assertTrue(any("through sr_reentry_milestone" in text and "sr_reentry_due_moon_landing = yes" in text
                            for text in added), added)
        self.assertIn("space_exploration", data["guaranteed"]["technologies"])
        self.assertEqual(self.script.unknown_adds, [])

    def test_a_banking_draw_has_its_pool_s_technology(self):
        data = self.analyze("banking_cycle_events.5")
        self.assertFalse(data["trigger"]["present"])
        self.assertIn("railways", data["guaranteed"]["technologies"])

    def test_json_and_trigger_from_the_command_line(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(eg.main(["augmentation_events.1", "--json"]), 0)
        printed = json.loads(out.getvalue())
        (data,) = printed["events"]
        self.assertTrue(any("te_debug_" in note for note in printed["notes"]))
        self.assertEqual(data["event"], "augmentation_events.1")
        self.assertEqual(data["routes"][0]["kind"], "journal_entry")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(eg.main(["--trigger", "has_augmentation_tech"]), 0)
        self.assertIn("scripted trigger has_augmentation_tech tests: one of", out.getvalue())


if __name__ == "__main__":
    unittest.main()
