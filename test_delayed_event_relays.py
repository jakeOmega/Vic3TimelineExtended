"""The hidden relays that wait out a delay for an event whose trigger is false
on the day it is queued (#1596).

A delayed `trigger_event` seems to drop its event when the event's trigger is
false when queued (scripting_best_practices.md § "A Delayed `trigger_event`
Re-Checks Its Trigger When It Fires"). Each popup below was queued on such a
day; it now waits in a hidden relay with no trigger, which opens it undelayed
when due. These tests hold each relay to that shape and fail if any script
queues the popup with a delay again. The judiciary's relays (.7, .8) and the
sanctions enforcer's (un_events.43) have their own tests.
"""
from __future__ import annotations

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

# relay -> (its file, the popup it opens, whether it opens it as a popup)
RELAYS = {
    "decolonization_events.81": ("events/decolonization_events.txt", "decolonization_events.15", False),
    "decolonization_events.82": ("events/decolonization_events.txt", "decolonization_events.22", False),
    "extra_law_events.91": ("events/extra_law_events.txt", "extra_law_events.26", False),
    "extra_law_events.92": ("events/extra_law_events.txt", "extra_law_events.27", False),
    "nuclear_custody.13": ("events/nuclear_custody_events.txt", "nuclear_custody.6", True),
    "nuclear_custody.14": ("events/nuclear_custody_events.txt", "nuclear_custody.11", True),
    # Not a trigger false when queued: one that must be read again a year on (a resolution that lapsed meanwhile).
    "un_vote.9": ("events/un_vote_events.txt", "un_vote.2", False),
}


def _read(rel: str) -> str:
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as fh:
        return fh.read()


def _block(text: str, name: str) -> str:
    m = re.search(r"^" + re.escape(name) + r" = \{", text, re.M)
    assert m, name
    depth, i = 0, m.end() - 1
    while True:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[m.start():i + 1]
        i += 1


def _script_files():
    for sub in ("events", "common"):
        for root, _d, files in os.walk(os.path.join(REPO, sub)):
            for f in files:
                if f.endswith(".txt"):
                    yield os.path.relpath(os.path.join(root, f), REPO)


class RelayTests(unittest.TestCase):
    def test_each_relay_is_hidden_with_no_trigger_and_opens_its_popup(self):
        for relay, (rel, popup, as_popup) in RELAYS.items():
            with self.subTest(relay=relay):
                block = _block(_read(rel), relay)
                self.assertIn("hidden = yes", block)
                self.assertNotIn("trigger = {", re.sub(r"trigger_event = \{[^}]*\}", "", block))
                call = "trigger_event = { id = %s%s }" % (popup, " popup = yes" if as_popup else "")
                self.assertIn(call, block, "opened undelayed, so its own trigger decides on the day")

    def test_no_script_queues_a_relayed_popup_with_a_delay(self):
        popups = {p for _f, p, _pp in RELAYS.values()}
        pattern = re.compile(r"trigger_event = \{ id = (%s) [^}]*\b(?:days|months|years) ="
                             % "|".join(re.escape(p) for p in popups))
        for rel in _script_files():
            for n, line in enumerate(_read(rel).splitlines(), 1):
                if pattern.search(line.split("#")[0]):
                    self.fail(f"{rel}:{n} queues a relayed popup with a delay: {line.strip()}")

    def test_each_relay_is_queued(self):
        texts = "\n".join(_read(rel) for rel in _script_files())
        for relay in RELAYS:
            with self.subTest(relay=relay):
                self.assertRegex(texts, r"trigger_event = \{ id = %s (?:days|months|years) = \d+ \}"
                                 % re.escape(relay))

    def test_the_last_call_checks_the_vote_again(self):
        # un_vote.6 runs 360 days after it is queued: a resolution closed
        # early takes no last call even if its trigger is read only then.
        block = _block(_read("events/un_vote_events.txt"), "un_vote.6")
        immediate = block[block.index("immediate = {"):]
        self.assertIn("scope:un_resolution ?= { has_tag = un_res_voting }", immediate)
        self.assertLess(immediate.index("has_tag = un_res_voting"), immediate.index("un_vote_refresh_leans"))

    def test_the_delegation_sort_checks_the_vote_again(self):
        # un_vote.7 runs a day after it is queued. A vote that closed overnight has no lock variable left: the
        # read of it must not fail, and nothing is sorted.
        block = _block(_read("events/un_vote_events.txt"), "un_vote.7")
        immediate = block[block.index("immediate = {"):]
        self.assertIn("global_var:un_active_resolution ?= { save_scope_as = un_resolution }", immediate)
        self.assertNotRegex(immediate, r"global_var:un_active_resolution = \{")
        self.assertIn("scope:un_resolution ?= { has_tag = un_res_voting }", immediate)
        self.assertLess(immediate.index("has_tag = un_res_voting"), immediate.index("un_deleg_reassign_rows"))

    def test_the_results_keep_the_trigger_the_relay_leaves_to_them(self):
        # un_vote.2 decides the vote in its immediate and applies the outcome in its option. Its trigger is what
        # stops that for a resolution that lapsed within the year, and the relay is what has it read on the day.
        block = _block(_read("events/un_vote_events.txt"), "un_vote.2")
        trigger = block[block.index("\ttrigger = {"):block.index("\timmediate = {")]
        self.assertIn("scope:un_resolution ?= { has_tag = un_res_voting }", trigger)
        self.assertIn("je:je_united_nations ?= { has_modifier = un_member_modifier }", trigger)


if __name__ == "__main__":
    unittest.main()
