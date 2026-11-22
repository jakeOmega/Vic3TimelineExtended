# -*- coding: utf-8 -*-
"""A sanctions regime's ways out (docs/systems/un_redesign_design.md §0.12a).

A regime (un_sanctions_target_modifier on the target, its enforcer recorded in
un_sanctions_enforced_by) ends when its enforcer presses Lift Sanctions, when
the Assembly carries the target's petition to lift it, when its enforcer stops
enforcing it, or when the UN dissolves. Before 2026-10-16 a regime whose
enforcer left the UN stood until some other enforcer happened to press Lift
Sanctions, which might never happen. The monthly update now lapses it.

The topic's wiring as a charter-business topic (gates, hooks, classification,
loc) is in test_un_charter_business.py's TOPICS. This file checks what is
particular to it: the lift itself, the monthly upkeep of every regime, the
paths that must forget a regime's months, and how the enforcer's choice
(un_events.5) is sent when a regime starts.

Run: python3 -m unittest test_un_lift_sanctions -v
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


JUSTICE_EFFECTS = _path("common", "scripted_effects", "un_justice_effects.txt")
JUSTICE_TRIGGERS = _path("common", "scripted_triggers", "un_justice_triggers.txt")
JUSTICE_VALUES = _path("common", "script_values", "un_justice_values.txt")
DOSSIER_TRIGGERS = _path("common", "scripted_triggers", "un_dossier_triggers.txt")
BUTTONS = _path("common", "scripted_buttons", "un_buttons.txt")
LADDER = _path("common", "scripted_effects", "un_ladder_effects.txt")
VOTE_EVENTS = _path("events", "un_vote_events.txt")
UN_EVENTS = _path("events", "un_events.txt")
MESSAGES = _path("common", "messages", "un_justice_messages.txt")
LOC_DIR = _path("localization", "english")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _flat(text):
    return re.sub(r"\s+", " ", text)


def _block(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


def _loc():
    keys = set()
    for name in sorted(os.listdir(LOC_DIR)):
        if not name.endswith(".yml") or name.startswith("te_unused"):
            continue
        with open(os.path.join(LOC_DIR, name), encoding="utf-8-sig") as f:
            for line in f:
                m = re.match(r"^ ([A-Za-z0-9_.\-]+):\d* ", line)
                if m:
                    keys.add(m.group(1))
    return keys


class LiftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _read(JUSTICE_EFFECTS)

    def test_the_lift_ends_every_part_of_the_regime(self):
        body = _flat(_block(self.effects, "un_sanctions_lift_regime"))
        # The regime is its variable: the entry declares the modifier from it (#1404).
        for part in ("if = { limit = { has_variable = un_sanctions_target_on } remove_variable = un_sanctions_target_on }",
                     "remove_variable = un_sanctions_enforced_by",
                     "remove_variable = un_sanctions_months",
                     "un_teeth_lift_embargoes = yes"):
            with self.subTest(part=part):
                self.assertIn(part, body)
        # Its enforcer is released, so it may table sanctions again.
        self.assertIn("var:un_sanctions_enforced_by ?= { if = { limit = { has_modifier = "
                      "un_sanctions_enforcer_modifier } remove_modifier = un_sanctions_enforcer_modifier } }", body)
        # The enforcer is read before the record that names it is removed.
        self.assertLess(body.index("var:un_sanctions_enforced_by ?="),
                        body.index("remove_variable = un_sanctions_enforced_by"))

    def test_a_carried_petition_lifts_unless_vetoed_and_is_moot_when_already_lifted(self):
        body = _flat(_block(self.effects, "un_lift_sanctions_on_carried"))
        vetoed, rest = body.split("else_if", 1)
        self.assertIn("has_tag = un_res_vetoed", vetoed)
        self.assertNotIn("un_sanctions_lift_regime", vetoed)
        carried, moot = rest.split("else =", 1)
        self.assertIn("un_sanctions_regime_on = yes", carried)
        self.assertIn("un_sanctions_lift_regime = yes", carried)
        self.assertIn("un_vote_lift_sanctions_moot_tt", moot)
        self.assertNotIn("un_sanctions_lift_regime", moot)


class MonthlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _read(JUSTICE_EFFECTS)
        cls.triggers = _read(JUSTICE_TRIGGERS)
        cls.update = _flat(_block(cls.effects, "un_sanctions_regime_monthly_update"))

    def test_the_owner_runs_it_every_month(self):
        self.assertIn("un_sanctions_regime_monthly_update = yes",
                      _flat(_block(self.effects, "un_justice_monthly_update")))

    def test_an_orphaned_regime_lapses_and_a_human_target_is_told(self):
        lapse = self.update[:self.update.index("un_sanctions_months")]
        self.assertIn("limit = { un_sanctions_regime_orphaned = yes }", lapse)
        self.assertIn("post_notification = un_sanctions_lapsed_notice", lapse)
        self.assertIn("is_ai = no", lapse)
        self.assertIn("un_sanctions_lift_regime = yes", lapse)

    def test_orphaned_means_recorded_and_not_enforced(self):
        body = _flat(_block(self.triggers, "un_sanctions_regime_orphaned"))
        # A regime from an older save names no one and is left alone.
        self.assertIn("has_variable = un_sanctions_enforced_by", body)
        self.assertIn("NOT = { var:un_sanctions_enforced_by ?= { has_modifier = un_sanctions_enforcer_modifier } }",
                      body)

    def test_the_regime_is_its_variable(self):
        # A revolution's winner inherits the variable, and the entry declares
        # the modifier from it (#1404), so nothing re-applies it any more.
        self.assertNotIn("add_modifier", self.update)
        self.assertEqual(_flat(_block(self.triggers, "un_sanctions_regime_on")).strip(),
                         "has_variable = un_sanctions_target_on")
        vote = _flat(_read(_path("events", "un_vote_events.txt")))
        self.assertIn("show_as_tooltip = { je:je_united_nations ?= { add_modifier = { "
                      "name = un_sanctions_target_modifier multiplier = un_enforcement } } } "
                      "set_variable = un_sanctions_target_on set_variable = { name = un_sanctions_enforced_by "
                      "value = ROOT }", vote)

    def test_each_regime_counts_its_months(self):
        self.assertIn("change_variable = { name = un_sanctions_months add = 1 }", self.update)
        self.assertIn("set_variable = { name = un_sanctions_months value = 0 }", self.update)

    def test_an_idle_enforcer_is_released_only_while_every_regime_names_one(self):
        release = self.update[self.update.index("un_sanctions_regime_unrecorded"):]
        self.assertTrue(release.startswith("un_sanctions_regime_unrecorded = yes } }"), release[:80])
        self.assertIn("save_temporary_scope_as = un_sanctions_enforcer_check", release)
        self.assertIn("limit = { un_sanctions_enforcer_idle = yes } remove_modifier = un_sanctions_enforcer_modifier",
                      release)
        idle = _flat(_block(self.triggers, "un_sanctions_enforcer_idle"))
        self.assertIn("var:un_sanctions_enforced_by ?= scope:un_sanctions_enforcer_check", idle)
        unrecorded = _flat(_block(self.triggers, "un_sanctions_regime_unrecorded"))
        self.assertIn("un_sanctions_regime_on = yes NOT = { has_variable = un_sanctions_enforced_by }", unrecorded)


class ForgetTheMonthsTests(unittest.TestCase):
    """Every path that ends a regime forgets its months, or a later regime on
    the same country would start old and be easier to lift."""

    def test_the_enforcers_button(self):
        # The button and the panel's Lift Ours both run un_sanctions_lift_ours
        # (the 2026-10-27 audit, UN-9 and UN-10).
        button = _flat(_block(_read(BUTTONS), "un_lift_sanctions_button"))
        self.assertIn("un_sanctions_lift_ours = yes", button)
        helper = _flat(_block(_read(JUSTICE_EFFECTS), "un_sanctions_lift_ours"))
        loop = helper[helper.index("every_country"):]
        self.assertIn("if = { limit = { has_variable = un_sanctions_target_on } remove_variable = un_sanctions_target_on }", loop)
        self.assertIn("remove_variable = un_sanctions_months", loop)

    def test_a_dissolution(self):
        strip = _flat(_block(_read(LADDER), "un_dissolve_strip_country"))
        self.assertIn("if = { limit = { has_variable = un_sanctions_target_on } remove_variable = un_sanctions_target_on }", strip)
        on_dissolve = _flat(_block(_read(JUSTICE_EFFECTS), "un_justice_on_dissolve"))
        self.assertIn("limit = { has_variable = un_sanctions_months } remove_variable = un_sanctions_months",
                      on_dissolve)

    def test_nothing_else_removes_the_regime(self):
        sites = []
        for root in ("common", "events"):
            for dirpath, _dirs, files in os.walk(_path(root)):
                for name in files:
                    if name.endswith(".txt"):
                        path = os.path.join(dirpath, name)
                        if "remove_variable = un_sanctions_target_on" in _read(path):
                            sites.append(os.path.relpath(path, REPO))
        self.assertEqual(sorted(sites), sorted([
            os.path.join("common", "scripted_effects", "un_justice_effects.txt"),
            os.path.join("common", "scripted_effects", "un_ladder_effects.txt"),
        ]))


class LeanTests(unittest.TestCase):
    def test_the_lean_reads_the_enforcer_the_embargoes_the_record_and_the_age(self):
        values = _read(JUSTICE_VALUES)
        body = _flat(_block(values, "un_lean_interests_lift_sanctions"))
        self.assertIn("limit = { NOT = { scope:un_vote_target ?= this } }", body)
        # The enforcer stands by the regime only while it still dislikes the target.
        self.assertIn("limit = { scope:un_vote_target ?= { var:un_sanctions_enforced_by ?= ROOT } "
                      "un_lift_sanctions_ill_disposed = yes } add = un_lean_lift_enforcer", body)
        self.assertIn("is_target_in_variable_list = { name = un_embargo_by target = ROOT }", body)
        for term in ("un_lean_lift_sanctions_grounds", "un_lean_lift_sanctions_fresh"):
            self.assertIn(f"add = {term}", body)
        grounds = _flat(_block(values, "un_lean_lift_sanctions_grounds"))
        self.assertIn("add = un_case_threshold_sanctions scope:un_vote_target = { subtract = un_case_strength }",
                      grounds)
        fresh = _flat(_block(values, "un_lean_lift_sanctions_fresh"))
        self.assertIn("add = un_lift_fresh_months scope:un_vote_target = { subtract = un_disp_sanctions_months } "
                      "min = 0 multiply = un_lean_lift_fresh_per_month", fresh)


class DislikeTests(unittest.TestCase):
    """Only a member that still dislikes the petitioner (a rival, or relations
    Cold or worse) stands by the regime it enforces or vetoes the petition
    (owner, 2026-10-16)."""

    def test_dislike_is_rivalry_or_cold_relations(self):
        body = _flat(_block(_read(JUSTICE_TRIGGERS), "un_lift_sanctions_ill_disposed"))
        self.assertIn("scope:un_vote_target ?= { OR = { has_diplomatic_pact = { who = ROOT type = rivalry } "
                      "relations:root <= relations_threshold:cold } }", body)

    def test_the_ai_vetoes_a_petition_only_from_dislike(self):
        body = _flat(_block(_read(DOSSIER_TRIGGERS), "un_vote_ai_should_veto"))
        self.assertIn("OR = { NOT = { scope:un_resolution ?= { has_tag = un_topic_lift_sanctions } } "
                      "un_lift_sanctions_ill_disposed = yes }", body)


class VoteThreeTests(unittest.TestCase):
    def test_accepting_or_denouncing_a_lift_moves_no_standing(self):
        text = _read(VOTE_EVENTS)
        start = text.index("un_vote.3 = {")
        event = _flat(text[start:])
        for tt in ("un_standing_complied_tt", "un_standing_defied_tt"):
            with self.subTest(tooltip=tt):
                head = event[:event.index(f"text = {tt}")]
                gate = head[head.rindex("if = { limit = {"):]
                self.assertIn("NOT = { scope:un_resolution ?= { has_tag = un_topic_lift_sanctions } }", gate)


def _inner(body, opener):
    """The inside of the first block in `body` whose opening line matches
    `opener` (a regex anchored at a line start, tabs included)."""
    m = re.search(opener, body, re.M)
    if m is None:
        raise AssertionError(f"{opener!r} not found")
    depth = 0
    for i in range(m.end() - 1, len(body)):
        if body[i] == "{":
            depth += 1
        elif body[i] == "}":
            depth -= 1
            if depth == 0:
                return body[m.end():i]
    raise AssertionError(f"{opener!r} is not closed")


class EnforcementRelayTests(unittest.TestCase):
    """#1596: un_vote.2 adds the enforcer modifier and sets the target's regime
    in the block that queues the enforcer's choice, so un_events.5's trigger is
    false on the day it is queued, and a delayed event whose trigger is false
    then seems to be dropped. The three months wait in the hidden un_events.43,
    which has no trigger and opens un_events.5 on the day if its trigger holds
    (the pattern of te_judiciary_events.7 and .8)."""

    @classmethod
    def setUpClass(cls):
        cls.events = _read(UN_EVENTS)
        cls.relay = _block(cls.events, "un_events.43")

    def test_the_vote_queues_the_relay_with_the_target_saved(self):
        vote = _flat(_read(VOTE_EVENTS))
        self.assertIn("add_modifier = { name = un_sanctions_enforcer_modifier } hidden_effect = { "
                      "scope:un_vote_target = { save_scope_as = sanctioned_country } "
                      "trigger_event = { id = un_events.43 days = 90 } }", vote)

    def test_the_relay_has_no_trigger_and_opens_the_popup_at_once(self):
        self.assertNotRegex(self.relay, r"(?m)^\ttrigger\s*=")
        self.assertIn("hidden = yes", self.relay)
        immediate = _flat(_inner(self.relay, r"^\timmediate\s*=\s*\{"))
        self.assertTrue(immediate.strip().startswith("if = { limit = {"), immediate[:60])
        self.assertIn("trigger_event = { id = un_events.5 }", immediate)

    def test_the_relay_restates_the_popups_trigger(self):
        popup = _block(self.events, "un_events.5")
        trigger = _flat(_inner(popup, r"^\ttrigger\s*=\s*\{")).strip()
        limit = _flat(_inner(self.relay, r"^\t\t\tlimit\s*=\s*\{")).strip()
        self.assertEqual(limit, trigger, "un_events.43's limit must be un_events.5's trigger")

    @staticmethod
    def _sends(event_id):
        sites = []
        pattern = r"trigger_event\s*=\s*\{[^}]*\b" + re.escape(event_id) + r"(?![0-9])[^}]*\}"
        for root in ("common", "events"):
            for dirpath, _dirs, files in os.walk(_path(root)):
                for name in sorted(files):
                    if name.endswith(".txt"):
                        path = os.path.join(dirpath, name)
                        for m in re.finditer(pattern, _read(path)):
                            sites.append((os.path.relpath(path, REPO), _flat(m.group(0))))
        return sites

    def test_one_site_sends_each(self):
        # un_vote.2 alone queues the relay, once per adopted regime, and the
        # relay alone sends un_events.5, undelayed: the popup comes once per
        # regime and never waits in the queue on a trigger read too early.
        self.assertEqual(self._sends("un_events.43"),
                         [(os.path.join("events", "un_vote_events.txt"),
                           "trigger_event = { id = un_events.43 days = 90 }")])
        self.assertEqual(self._sends("un_events.5"),
                         [(os.path.join("events", "un_events.txt"),
                           "trigger_event = { id = un_events.5 }")])


class NoticeTests(unittest.TestCase):
    def test_the_lapse_notice(self):
        self.assertIn("un_sanctions_lapsed_notice", _read(MESSAGES))
        loc = _loc()
        for suffix in ("name", "desc", "tooltip"):
            self.assertIn(f"notification_un_sanctions_lapsed_notice_{suffix}", loc)
        for key in ("je_un_chamber_propose_preview_lift_sanctions",
                    "je_un_chamber_propose_preview_lift_sanctions_unrecorded",
                    "un_vote_lift_sanctions_moot_tt", "un_vote_lift_sanctions_passed_tt",
                    "un_vote_lift_sanctions_passed_vetoed_tt", "un_lift_sanctions_grounds_tt",
                    "un_vote.1.d_lift_sanctions_enforcer"):
            with self.subTest(key=key):
                self.assertIn(key, loc)


if __name__ == "__main__":
    unittest.main()
