"""Unit tests for delayed_event_trigger_audit (#1596).

It classes each delayed event with a top-level trigger by whether that
trigger can hold on the day it is queued. The crux: a modifier added before
the call in what runs on the way to it is caught, one added in another option
or an exclusive branch is not; a `modifier:` read is a lag only where a law
has just changed.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from delayed_event_trigger_audit import audit, render_report

BOM = "﻿"


def _mod(files: dict[str, str]) -> str:
    root = tempfile.mkdtemp()
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(BOM + text)
    return root


EVENTS = """namespace = t
t.1 = {
	type = country_event
	hidden = yes
	trigger = { has_modifier = m_packed }
	immediate = { }
}
t.2 = {
	type = country_event
	trigger = { has_variable = v_set }
	option = { name = a }
}
t.3 = {
	type = country_event
	hidden = yes
	trigger = { my_lagging_trigger = yes }
	immediate = { }
}
t.4 = {
	type = country_event
	hidden = yes
	trigger = { is_at_war = yes } # REVIEWED 2026-11-12 (delayed_trigger): checked by hand
	immediate = { }
}
t.5 = {
	type = country_event
	hidden = yes
	immediate = { }
}
t.6 = {
	type = country_event
	hidden = yes
	trigger = { is_at_war = yes }
	immediate = { }
}
"""


class ClassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = _mod({
            "events/t_events.txt": EVENTS,
            "common/scripted_triggers/t.txt": "my_lagging_trigger = { modifier:country_x_bool = yes }\n",
            "common/scripted_effects/t.txt": """pack = {
	add_modifier = { name = m_packed years = 10 }
	hidden_effect = { trigger_event = { id = t.1 days = 365 } }
}
set_then_queue = {
	set_variable = { name = v_set days = 30 }
	trigger_event = { id = t.2 days = 10 }
}
queue_plain = {
	trigger_event = { id = t.4 days = 3 }
	trigger_event = { id = t.5 days = 3 }
	trigger_event = { id = t.6 months = 1 }
	trigger_event = { id = t.6 }
}
""",
            "common/on_actions/t.txt": """on_law_activated = { on_actions = { t_law_hook } }
t_law_hook = { effect = { owner = { trigger_event = { id = t.3 days = 7 } } } }
""",
        })
        cls.result = audit(mod_path=root)
        cls.by_event = {t.event: t for t in cls.result.targets}

    def test_counts(self):
        self.assertEqual(self.result.calls, 6, "the undelayed call is not counted")
        self.assertEqual(self.result.delayed_targets, 6)
        self.assertNotIn("t.5", self.by_event, "an event with no trigger is not listed")

    def test_a_modifier_added_before_the_call(self):
        t = self.by_event["t.1"]
        self.assertEqual(t.cls, "likely_false")
        self.assertIn("modifier_same_block", t.calls[0].reason)

    def test_a_variable_set_before_the_call(self):
        self.assertEqual(self.by_event["t.2"].cls, "set_before")

    def test_a_modifier_read_after_a_law_change(self):
        t = self.by_event["t.3"]
        self.assertEqual(t.cls, "likely_false")
        self.assertIn("law_lag", t.calls[0].reason)

    def test_reviewed(self):
        t = self.by_event["t.4"]
        self.assertEqual(t.cls, "reviewed")
        self.assertEqual(t.exemption["date"], "2026-11-12")

    def test_the_rest_is_for_review(self):
        self.assertEqual(self.by_event["t.6"].cls, "review")

    def test_report_lists_each_class(self):
        report = render_report(self.result)
        for event in ("t.1", "t.2", "t.3", "t.4", "t.6"):
            self.assertIn(f"`{event}`", report)
        self.assertIn("- with a non-empty top-level trigger: 5", report)


    def test_strict_fails_on_the_unreviewed(self):
        self.assertEqual(sorted(t.event for t in self.result.unreviewed), ["t.1", "t.3", "t.6"],
                         "likely_false and review fail; set_before and reviewed do not")
        self.assertTrue(self.result.failed)


class GraphTests(unittest.TestCase):
    """Sites through helpers, empty triggers, stale tags, the cancels class."""

    @classmethod
    def setUpClass(cls):
        root = _mod({
            "events/t_events.txt": """namespace = t
t.1 = {
	type = country_event
	hidden = yes
	trigger = { is_at_war = yes } # REVIEWED 2026-11-13 (delayed_trigger): cancels: the war ends
	immediate = { }
}
t.2 = {
	type = country_event
	hidden = yes
	trigger = {
		# fired by the pulse
	}
	immediate = { }
}
t.3 = {
	type = country_event
	hidden = yes
	trigger = { is_at_war = yes } # REVIEWED 2026-11-13 (delayed_trigger): nothing queues this any more
	immediate = { }
}
t.4 = {
	type = country_event
	hidden = yes
	trigger = { is_at_war = yes }
	immediate = { }
}
""",
            "common/scripted_effects/t.txt": """send_later = {
	trigger_event = { id = $EVENT$ days = 5 }
}
caller = {
	send_later = { EVENT = t.4 }
	trigger_event = { id = t.1 days = 2 }
	trigger_event = { id = t.2 days = 2 }
}
""",
        })
        cls.result = audit(mod_path=root)
        cls.by_event = {t.event: t for t in cls.result.targets}

    def test_an_id_passed_to_a_helper_counts_at_its_caller(self):
        t = self.by_event["t.4"]
        self.assertEqual(t.cls, "review")
        self.assertEqual(t.calls[0].entity, "caller")
        self.assertIn("through `send_later`", t.calls[0].delay)
        self.assertNotIn("$EVENT$", self.result.unresolved)

    def test_an_empty_trigger_is_not_listed(self):
        self.assertNotIn("t.2", self.by_event)

    def test_a_tag_on_an_event_nothing_delays_is_stale(self):
        self.assertEqual([s.event for s in self.result.stale], ["t.3"])

    def test_cancels(self):
        t = self.by_event["t.1"]
        self.assertEqual(t.cls, "reviewed")
        self.assertTrue(t.cancels)
        self.assertIn("also cancels the event: 1", render_report(self.result))


class BranchTests(unittest.TestCase):
    def _cls(self, effects: str) -> str:
        root = _mod({"events/t_events.txt": EVENTS, "common/scripted_effects/t.txt": effects})
        return {t.event: t for t in audit(mod_path=root).targets}["t.1"].cls

    def test_another_option_does_not_count(self):
        root = _mod({"events/t_events.txt": EVENTS + """t.9 = {
	type = country_event
	option = { name = a add_modifier = { name = m_packed } }
	option = { name = b trigger_event = { id = t.1 days = 5 } }
}
"""})
        self.assertEqual({t.event: t for t in audit(mod_path=root).targets}["t.1"].cls, "review")

    def test_an_if_before_the_else_does_not_count(self):
        self.assertEqual(self._cls("""e = {
	if = { limit = { always = yes } add_modifier = { name = m_packed } }
	else = { trigger_event = { id = t.1 days = 5 } }
}
"""), "review")

    def test_another_random_list_branch_does_not_count(self):
        self.assertEqual(self._cls("""e = {
	random_list = {
		10 = { add_modifier = { name = m_packed } }
		10 = { trigger_event = { id = t.1 days = 5 } }
	}
}
"""), "review")

    def test_an_earlier_if_in_the_same_block_counts(self):
        self.assertEqual(self._cls("""e = {
	if = { limit = { always = yes } add_modifier = m_packed }
	trigger_event = { id = t.1 days = 5 }
}
"""), "likely_false")


class ModTests(unittest.TestCase):
    def test_the_court_events_are_queued_without_a_trigger(self):
        result = audit()
        by_event = {t.event: t for t in result.targets}
        for event in ("te_judiciary_events.1", "te_judiciary_events.5", "te_judiciary_events.34"):
            self.assertNotIn(event, by_event, f"{event} is queued with a delay again, with its trigger")
        self.assertEqual(by_event["te_judiciary_events.9"].cls, "reviewed", "the self-check's probe")

    def test_the_mod_is_clean(self):
        result = audit()
        self.assertEqual([t.event for t in result.unreviewed], [])
        self.assertEqual([s.event for s in result.stale], [])

    def test_the_report_is_committed(self):
        from path_constants import mod_path
        with open(os.path.join(mod_path, "docs", "engine", "delayed_event_trigger_report.md"),
                  encoding="utf-8") as fh:
            report = fh.read()
        self.assertIn("# Delayed events with a trigger", report)


if __name__ == "__main__":
    unittest.main()
