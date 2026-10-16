# -*- coding: utf-8 -*-
"""What a carried resolution does to the members, as the UN panel's terms say.

PR 968's audit of the terms tooltips found seven places where the script did
something the design and its own comments said it should not. Each was fixed
rather than written into the tooltips, and these tests pin the fixes:

- the decolonization declaration's pressure is the UN's own modifier, not the
  crackdown event's;
- un_vote.3 books no compliance or defiance on a resolution a veto blocked or
  softened;
- the peacekeeping programme's ten-year cooldown lands on the pledgers, when
  they pledge;
- a bloc leader's +50 leverage over a requester is paid only for a pledge;
- the sanctions proposer becomes the enforcer only when a regime starts;
- a target's yes on an expulsion, a mandate or a court referral is an
  ordinary yes;
- electoral observers halve Election Interference only with some strength;
- the three never-applied reservation modifiers are gone.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


def _raw(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _read(path):
    return re.sub(r"#[^\n]*", "", _raw(path))


def _close(text, start):
    """Index of the brace that closes the first ``{`` at or after ``start``."""
    depth = 0
    for i in range(text.index("{", start), len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _children(text, key):
    """Bodies of every ``key = { ... }`` block directly or deeper in ``text``."""
    out = []
    for m in re.finditer(r"(?<![\w.:])" + re.escape(key) + r"\s*=\s*\{", text):
        out.append(text[m.end():_close(text, m.end() - 1)])
    return out


def _ifs(text):
    """(limit, body) for every ``if``/``else_if`` in ``text``."""
    out = []
    for body in _children(text, "if") + _children(text, "else_if"):
        limits = re.match(r"\s*limit\s*=\s*\{", body)
        limit = body[limits.end():_close(body, limits.end() - 1)] if limits else ""
        out.append((limit, body))
    return out


def _squash(text):
    return re.sub(r"\s+", " ", text)


VOTE_EVENTS = _path("events", "un_vote_events.txt")
VOTE_EFFECTS = _path("common", "scripted_effects", "un_vote_effects.txt")
CAST_EFFECTS = _path("common", "scripted_effects", "un_vote_cast_effects.txt")
RESOLUTION_TRIGGERS = _path("common", "scripted_triggers", "un_resolution_triggers.txt")
MISSION_TRIGGERS = _path("common", "scripted_triggers", "un_mission_triggers.txt")
COVERT_EFFECTS = _path("common", "scripted_effects", "covert_warfare_effects.txt")
MODIFIERS = _path("common", "static_modifiers", "extra_modifiers.txt")
LOC = _path("localization", "english")


def _loc_keys():
    keys = {}
    for name in os.listdir(LOC):
        if name.endswith(".yml"):
            for m in re.finditer(r"^ ([\w.]+):\d+ \"(.*)\"$", _raw(os.path.join(LOC, name)), re.M):
                keys[m.group(1)] = m.group(2)
    return keys


def _fields(body):
    return dict(re.findall(r"^\s*(\w+)\s*=\s*(\S+)", body, re.M))


class DecolonizationPressureTests(unittest.TestCase):
    """The declaration used to hand out the crackdown event's
    anti_colonial_momentum_modifier, whose name and description speak of a
    crackdown on intellectuals, and skipped any country that had cracked down."""

    def test_un_vote_2_applies_its_own_modifier(self):
        events = _read(VOTE_EVENTS)
        self.assertNotIn("anti_colonial_momentum_modifier", events)
        loops = [b for b in _children(events, "every_country")
                 if "name = un_decolonization_pressure_modifier" in b]
        self.assertEqual(len(loops), 1)
        self.assertIn("NOT = { has_modifier = un_decolonization_pressure_modifier }", _squash(loops[0]))

    def test_same_effects_as_the_crackdowns(self):
        mods = _read(MODIFIERS)
        ours = _fields(_block(mods, "un_decolonization_pressure_modifier"))
        theirs = _fields(_block(mods, "anti_colonial_momentum_modifier"))
        self.assertEqual(ours, theirs)

    def test_named_described_and_shown_in_the_terms(self):
        loc = _loc_keys()
        self.assertIn("un_decolonization_pressure_modifier", loc)
        self.assertIn("un_decolonization_pressure_modifier_desc", loc)
        self.assertNotIn("crackdown", loc["un_decolonization_pressure_modifier_desc"].lower())
        self.assertIn("GetStaticModifier('un_decolonization_pressure_modifier').GetDesc",
                      loc["je_un_terms_decolonization"])
        self.assertNotIn("anti_colonial_momentum_modifier", loc["je_un_terms_decolonization"])


class VetoedAnswerTests(unittest.TestCase):
    """A veto that held leaves nothing binding: un_vote.3's options B and C
    move no standing and book no defiance on a vetoed resolution."""

    @classmethod
    def setUpClass(cls):
        event = _block(_read(VOTE_EVENTS), "un_vote.3")
        cls.options = _children(event, "option")
        cls.event = event

    def _standing_ifs(self, needle):
        return [lim for opt in self.options for lim, body in _ifs(opt)
                if needle in body and "un_resolution_is_binding = yes" in lim]

    def test_compliance_skips_a_vetoed_resolution(self):
        limits = self._standing_ifs("un_standing_gain")
        self.assertEqual(len(limits), 1)
        self.assertIn("NOT = { scope:un_resolution ?= { has_tag = un_res_vetoed } }", _squash(limits[0]))

    def test_defiance_skips_a_vetoed_resolution(self):
        limits = self._standing_ifs("un_dossier_record")
        self.assertEqual(len(limits), 1)
        self.assertIn("NOT = { scope:un_resolution ?= { has_tag = un_res_vetoed } }", _squash(limits[0]))

    def test_the_event_says_so(self):
        self.assertIn("desc = un_vote.3.d_choice_vetoed", self.event)
        self.assertIn("custom_tooltip = un_vote.3.c_vetoed_tt", self.event)
        loc = _loc_keys()
        for key in ("un_vote.3.d_choice_vetoed", "un_vote.3.c_vetoed_tt"):
            with self.subTest(key=key):
                self.assertIn(key, loc)
        self.assertIn("no veto has blocked or softened", loc["je_un_terms_common"])


class PeacekeepingPledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compliance = _block(_read(VOTE_EFFECTS), "un_vote_apply_resolution_compliance")

    def test_un_vote_2_puts_no_one_on_cooldown(self):
        # It ran before un_vote.3 enrolled anyone: new pledgers could leave at
        # once, and members that refused the mission were locked in again.
        self.assertNotIn("un_peacekeeping_cooldown", _read(VOTE_EVENTS))

    def test_the_pledge_puts_the_pledger_on_cooldown(self):
        pledge = [b for lim, b in _ifs(self.compliance)
                  if "un_resolution_peacekeeping_full = yes" in lim
                  and "un_peacekeeping_contributor_modifier" in b]
        self.assertEqual(len(pledge), 1)
        self.assertIn("name = un_peacekeeping_cooldown", pledge[0])

    def test_bloc_leverage_only_for_a_pledge(self):
        lever = [lim for lim, b in _ifs(self.compliance)
                 if "add_leverage" in b and "value = 50" in b]
        self.assertEqual(len(lever), 1)
        limit = _squash(lever[0])
        self.assertIn("country_rank >= rank_value:major_power", limit)
        self.assertIn("un_resolution_peacekeeping_full = yes", limit)
        self.assertNotIn("un_topic_peacekeeping_request", limit)
        self.assertNotIn("whether or not it pledges", _loc_keys()["je_un_terms_pledge_rules"])


class SanctionsEnforcerTests(unittest.TestCase):
    def test_enforcer_only_when_a_regime_starts(self):
        events = _read(VOTE_EVENTS)
        adds = [m.start() for m in re.finditer(r"add_modifier\s*=\s*\{\s*name\s*=\s*un_sanctions_enforcer_modifier", events)]
        self.assertEqual(len(adds), 1)
        guards = [lim for lim, body in _ifs(events)
                  if "un_sanctions_enforcer_modifier" in body
                  and "un_res_target_accepted" in lim
                  and "un_sanctions_target_modifier" not in body]
        self.assertEqual(len(guards), 1)
        self.assertIn("exists = scope:un_vote_target", guards[0])
        self.assertIn("NOT = { scope:un_resolution ?= { has_tag = un_res_target_accepted } }", _squash(guards[0]))


class TargetAcceptanceTests(unittest.TestCase):
    """Acceptance softens no expulsion, mandate or court referral, so the
    target's yes on one is not charged as a confession."""

    def test_trigger_excludes_the_three(self):
        body = _squash(_block(_read(RESOLUTION_TRIGGERS), "un_resolution_target_may_accept"))
        self.assertIn("un_resolution_accuses_target = yes", body)
        for topic in ("un_topic_expulsion", "un_topic_military_mandate", "un_topic_court_referral"):
            with self.subTest(topic=topic):
                self.assertIn("has_tag = " + topic, body)
        self.assertIn("NOR = {", body)

    def test_the_cast_and_the_event_name_use_it(self):
        cast = _block(_read(CAST_EFFECTS), "un_vote_cast_yes")
        confession = [lim for lim, b in _ifs(cast)
                      if "un_self_corrected_modifier" in b and "scope:un_vote_target ?= this" in lim]
        self.assertEqual(len(confession), 1)
        self.assertIn("un_resolution_target_may_accept = yes", confession[0])
        self.assertNotIn("un_resolution_accuses_target", confession[0])
        vote1 = _block(_read(VOTE_EVENTS), "un_vote.1")
        option_a = _children(vote1, "option")[0]
        self.assertIn("un_resolution_target_may_accept = yes", option_a)
        self.assertNotIn("not softened at all", _loc_keys()["UN_VOTE_ACCEPT_TARGET_TT"])


class ElectoralObserverTests(unittest.TestCase):
    def test_halving_needs_strength(self):
        body = _block(_read(COVERT_EFFECTS), "covert_op_election_confidence_effect")
        self.assertEqual(body.count("un_mission_hosts_with_strength = { TYPE = electoral }"), 2)
        self.assertNotIn("un_mission_hosts = {", body)
        trigger = _squash(_block(_read(MISSION_TRIGGERS), "un_mission_hosts_with_strength"))
        self.assertIn("has_tag = un_msn_$TYPE$", trigger)
        self.assertIn("var:un_msn_strength > 0", trigger)
        self.assertNotIn("whatever the mission's strength", _loc_keys()["je_un_terms_observer_request"])


class DeadReservationModifierTests(unittest.TestCase):
    DEAD = ("un_heritage_token_modifier", "un_human_rights_reservations_modifier",
            "un_law_of_sea_reservations_modifier")

    def test_gone_from_script_and_loc(self):
        loc = _loc_keys()
        for root, _dirs, files in os.walk(_path("common")):
            for name in files:
                if name.endswith(".txt"):
                    text = _read(os.path.join(root, name))
                    for mod in self.DEAD:
                        with self.subTest(file=name, modifier=mod):
                            self.assertNotIn(mod, text)
        for mod in self.DEAD:
            with self.subTest(modifier=mod):
                self.assertNotIn(mod, loc)
                self.assertNotIn(mod + "_desc", loc)


if __name__ == "__main__":
    unittest.main()
