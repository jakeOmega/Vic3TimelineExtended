# -*- coding: utf-8 -*-
"""The charter's new business (redesign phase 7): every hook the shared UN
machinery calls for the nine phase 7 decisions, requests and institutions
exists, and every topic is wired the way docs/systems/un_redesign_design.md
§0.12 says.

The two phase 7 conventions (cultural_diversity, nuclear_ban) are in
test_un_convention_registry.py's CONVENTIONS with the other conventions.

Each topic's own logic lives in its owner's files
(common/scripted_effects/un_charter_effects.txt names the owners); the shared
files reach it only through the names below. A name nothing defines is
engine-silent (an effect that does nothing, a value that reads 0), so this test
is what catches a half-wired topic.

Run: python3 -m unittest test_un_charter_business -v
"""

import os
import re
import unittest
from collections import namedtuple

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


PROPOSE_TRIGGERS = _path("common", "scripted_triggers", "un_propose_triggers.txt")
PROPOSE_EFFECTS = _path("common", "scripted_effects", "un_propose_effects.txt")
RESOLUTION_TRIGGERS = _path("common", "scripted_triggers", "un_resolution_triggers.txt")
CHARTER_EFFECTS = _path("common", "scripted_effects", "un_charter_effects.txt")
CHARTER_VALUES = _path("common", "script_values", "un_charter_values.txt")
DOSSIER = _path("common", "script_values", "un_dossier_values.txt")
BUTTONS = _path("common", "scripted_buttons", "un_buttons.txt")
JOURNAL = _path("common", "journal_entries", "je_united_nations.txt")
VOTE_EVENTS = _path("events", "un_vote_events.txt")
ON_ACTIONS = _path("common", "on_actions", "un_on_actions.txt")
LADDER = _path("common", "scripted_effects", "un_ladder_effects.txt")
LOC_DIR = _path("localization", "english")

# key        the topic: un_topic_<key> and un_propose_<key>_*
# reform     the charter level it needs (0: none)
# binding    vetoable
# blocks     a veto blocks it outright (no graduated form)
# two_thirds decided by two thirds of the members with a vote
# punitive   needs grounds (a case threshold)
# accuses    names a target it accuses
# names      names a country (selects a target)
# beneficiary  its target is the requester it helps
# tabled     writes its own fields on the resolution (un_<key>_on_tabled)
Topic = namedtuple("Topic", "key reform binding blocks two_thirds punitive accuses names beneficiary tabled")

TOPICS = (
    Topic("court_referral", 1, True, False, False, False, True, True, False, True),
    Topic("arms_embargo", 1, True, False, False, True, True, True, False, False),
    Topic("credentials", 1, False, False, True, True, True, True, False, False),
    Topic("standing_force", 1, True, True, False, False, False, False, False, False),
    Topic("observer_request", 1, False, False, False, False, False, False, True, False),
    Topic("food_reserve", 0, False, False, False, False, False, False, False, False),
    Topic("ceasefire", 2, True, False, False, True, True, True, False, True),
    Topic("development_fund", 2, False, False, False, False, False, False, False, False),
    Topic("referendum", 2, True, True, False, False, True, True, False, True),
)
KEYS = tuple(t.key for t in TOPICS)

# Every owner provides these, once (un_charter_effects.txt).
OWNER_HOOKS = (
    "un_justice_monthly_update", "un_order_monthly_update", "un_economy_monthly_update",
    "un_justice_on_dissolve", "un_order_on_dissolve", "un_economy_on_dissolve", "un_force_on_dissolve",
    "un_food_reserve_on_aid_mission_opened",
)


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


def _defined(*dirs):
    names = set()
    for d in dirs:
        root = _path(*d.split("/"))
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                if name.endswith(".txt"):
                    names |= set(re.findall(r"^([A-Za-z_][\w.]*)\s*=\s*\{",
                                            _read(os.path.join(dirpath, name)), re.M))
    return names


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


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = _read(PROPOSE_TRIGGERS)
        cls.effects = _read(PROPOSE_EFFECTS)

    def test_available_asks_the_owners_case(self):
        for t in TOPICS:
            with self.subTest(key=t.key):
                body = _flat(_block(self.triggers, f"un_propose_{t.key}_available"))
                self.assertIn("je:je_united_nations ?= { has_modifier = un_member_modifier }", body)
                self.assertIn(f"un_{t.key}_case_exists = yes", body)
                # The reform is never an availability gate: the row stays listed.
                self.assertNotIn("un_charter_has_reform", body)

    def test_possible_asks_the_reform_the_cooldown_and_the_owners_gates(self):
        for t in TOPICS:
            with self.subTest(key=t.key):
                body = _flat(_block(self.triggers, f"un_propose_{t.key}_possible"))
                reforms = re.findall(r"un_charter_has_reform_tt = \{ LEVEL = (\d) TT = un_charter_needs_reform_(\d)_tt \}", body)
                if t.reform:
                    self.assertEqual(reforms, [(str(t.reform), str(t.reform))])
                else:
                    self.assertEqual(reforms, [])
                self.assertIn(f"un_resolution_topic_on_cooldown = {{ TOPIC = {t.key} }}", body)
                self.assertIn(f"un_{t.key}_can_table = yes", body)

    def test_effect_opens_its_own_topic_and_names_its_pick(self):
        for t in TOPICS:
            with self.subTest(key=t.key):
                body = _flat(_block(self.effects, f"un_propose_{t.key}_effect"))
                self.assertIn(f"un_resolution_open = {{ TOPIC = {t.key} }}", body)
                self.assertEqual(f"un_{t.key}_select_target = yes" in body, t.names)
                self.assertEqual(f"un_{t.key}_on_tabled = yes" in body, t.tabled)
                if t.names:
                    self.assertIn(f"scope:un_{t.key}_pick ?= {{ save_scope_as = un_vote_target }}", body)
                    # The pick is named before the vote opens.
                    self.assertLess(body.index(f"un_{t.key}_select_target"), body.index("un_resolution_open"))


class ClassificationTests(unittest.TestCase):
    """The resolution triggers sort each topic as the design table says."""

    @classmethod
    def setUpClass(cls):
        text = _read(RESOLUTION_TRIGGERS)
        cls.lists = {
            name: set(re.findall(r"has_tag\s*=\s*un_topic_(\w+)", _block(text, name)))
            for name in ("un_resolution_is_binding", "un_resolution_veto_blocks",
                         "un_resolution_needs_supermajority", "un_resolution_is_punitive",
                         "un_resolution_accuses_target", "un_resolution_target_is_beneficiary")
        }
        thresholds = _block(_read(DOSSIER), "un_res_case_threshold")
        cls.thresholds = set(re.findall(r"has_tag\s*=\s*un_topic_(\w+)", thresholds))

    def test_each_list(self):
        for name, field in (("un_resolution_is_binding", "binding"),
                            ("un_resolution_veto_blocks", "blocks"),
                            ("un_resolution_needs_supermajority", "two_thirds"),
                            ("un_resolution_is_punitive", "punitive"),
                            ("un_resolution_target_is_beneficiary", "beneficiary")):
            with self.subTest(trigger=name):
                listed = self.lists[name] & set(KEYS)
                self.assertEqual(listed, {t.key for t in TOPICS if getattr(t, field)})

    def test_accusing_topics(self):
        # un_resolution_accuses_target lists the non-punitive accusers; the
        # punitive ones come through un_resolution_is_punitive.
        listed = (self.lists["un_resolution_accuses_target"] | self.lists["un_resolution_is_punitive"]) & set(KEYS)
        self.assertEqual(listed, {t.key for t in TOPICS if t.accuses})

    def test_a_blocked_topic_is_binding(self):
        for t in TOPICS:
            if t.blocks:
                with self.subTest(key=t.key):
                    self.assertTrue(t.binding)

    def test_each_punitive_topic_has_its_threshold(self):
        self.assertEqual(self.thresholds & set(KEYS), {t.key for t in TOPICS if t.punitive})


class HookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _defined("common/scripted_effects")
        cls.triggers = _defined("common/scripted_triggers")
        cls.values = _defined("common/script_values")
        cls.charter = _read(CHARTER_EFFECTS)
        cls.values_text = _read(CHARTER_VALUES)

    def test_every_owner_name_is_defined(self):
        for t in TOPICS:
            names = [
                (f"un_{t.key}_case_exists", self.triggers),
                (f"un_{t.key}_can_table", self.triggers),
                (f"un_{t.key}_on_carried", self.effects),
                (f"un_{t.key}_chamber_preview", self.effects),
                (f"un_lean_interests_{t.key}", self.values),
                (f"un_{t.key}_ai_chance", self.values),
            ]
            if t.names:
                names.append((f"un_{t.key}_select_target", self.effects))
            if t.tabled:
                names.append((f"un_{t.key}_on_tabled", self.effects))
            for name, pool in names:
                with self.subTest(key=t.key, name=name):
                    self.assertIn(name, pool)

    def test_every_owner_hook_is_defined(self):
        for name in OWNER_HOOKS:
            with self.subTest(name=name):
                self.assertIn(name, self.effects)

    def test_the_dispatchers_cover_every_topic(self):
        carried = _flat(_block(self.charter, "un_charter_on_carried"))
        lean = _flat(_block(self.values_text, "un_lean_charter_interests"))
        for t in TOPICS:
            with self.subTest(key=t.key):
                self.assertIn(f"has_tag = un_topic_{t.key} }} }} un_{t.key}_on_carried = yes", carried)
                self.assertIn(f"has_tag = un_topic_{t.key} }} }} add = un_lean_interests_{t.key}", lean)

    def test_the_shared_machinery_calls_the_dispatchers(self):
        self.assertIn("un_charter_on_carried = yes", _read(VOTE_EVENTS))
        self.assertIn("add = un_lean_charter_interests", _block(_read(DOSSIER), "un_lean_interests"))
        self.assertIn("un_charter_monthly_update = yes", _read(ON_ACTIONS))
        self.assertIn("un_charter_on_dissolve = yes", _block(_read(LADDER), "un_dissolve"))


class ButtonTests(unittest.TestCase):
    def test_every_topic_has_an_ai_button_on_the_journal_entry(self):
        buttons = _read(BUTTONS)
        journal = _read(JOURNAL)
        for t in TOPICS:
            with self.subTest(key=t.key):
                body = _flat(_block(buttons, f"un_propose_{t.key}_button"))
                self.assertIn(f"visible = {{ un_propose_{t.key}_available = yes }}", body)
                self.assertIn(f"possible = {{ un_propose_{t.key}_possible = yes }}", body)
                self.assertIn(f"value = un_{t.key}_ai_chance", body)
                self.assertIn(f"effect = {{ un_propose_{t.key}_effect = yes }}", body)
                self.assertRegex(journal, rf"scripted_button\s*=\s*un_propose_{t.key}_button\b")


class LocTests(unittest.TestCase):
    def test_every_key_the_framework_names_exists(self):
        loc = _loc()
        for t in TOPICS:
            up = t.key.upper()
            keys = [
                f"UN_PROPOSE_{up}", f"UN_PROPOSE_{up}_DESC", f"UN_PROPOSE_{up}_TT",
                f"je_un_chamber_propose_need_{t.key}", f"je_un_chamber_propose_topic_{t.key}",
                f"je_un_chamber_propose_no_case_{t.key}", f"je_un_chamber_topic_{t.key}",
                f"je_un_chamber_conseq_{t.key}", f"je_un_led_topic_{t.key}",
                f"un_vote.1.t_{t.key}", f"un_vote.1.d_{t.key}",
                f"un_vote.2.d_{t.key}_passed", f"un_vote.2.d_{t.key}_failed",
            ]
            if t.binding:
                keys += [f"je_un_chamber_conseq_{t.key}_vetoed", f"un_vote.2.d_{t.key}_passed_vetoed"]
            if t.accuses:
                keys.append(f"un_vote.1.d_{t.key}_target")
            for key in keys:
                with self.subTest(key=key):
                    self.assertIn(key, loc)

    def test_the_shared_keys_exist(self):
        loc = _loc()
        for key in ("un_charter_needs_reform_1_tt", "un_charter_needs_reform_2_tt",
                    "je_un_chamber_propose_needs_reform_1", "je_un_chamber_propose_needs_reform_2",
                    "je_un_chamber_sub_propose_justice", "je_un_chamber_sub_propose_institutions",
                    "je_un_chamber_outcome_passed_vetoed_blocked"):
            with self.subTest(key=key):
                self.assertIn(key, loc)


if __name__ == "__main__":
    unittest.main()
