# -*- coding: utf-8 -*-
"""UN membership for subjects (docs/systems/un_redesign_design.md §0.8).

Diplomatic autonomy decides who may join and whose seat is active; a member
that loses it keeps its membership with its representation suspended. The
rule is carried by a few scripted triggers asked at many gates, and nothing in
the engine checks that a gate asks them. These tests do.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block."""
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


TRIGGERS = _path("common", "scripted_triggers", "un_membership_triggers.txt")


class EligibilityTests(unittest.TestCase):
    def test_eligible_types_are_the_autonomous_ones(self):
        body = _block(_read(TRIGGERS), "un_membership_eligible")
        types = set(re.findall(r"is_subject_type\s*=\s*(\w+)", body))
        self.assertEqual(types, {
            "subject_type_dominion",
            "subject_type_protectorate",
            "subject_type_tributary",
        })
        self.assertIn("is_subject = no", body)
        self.assertIn("is_country_type = decentralized", body)

    def test_billing_needs_a_represented_overlord(self):
        body = _block(_read(TRIGGERS), "un_dues_billed_to_overlord")
        self.assertIn("un_representation_suspended = yes", body)
        self.assertRegex(body, r"overlord\s*\?=\s*\{\s*un_member_represented = yes")

    def test_every_way_in_asks_eligibility(self):
        cases = [
            (("common", "scripted_buttons", "un_buttons.txt"), "un_join_button"),
            (("common", "scripted_effects", "un_ladder_effects.txt"), "un_charter_invitations"),
            (("events", "un_events.txt"), "un_events.1"),
            (("events", "un_events.txt"), "un_events.10"),
            (("common", "scripted_triggers", "un_teeth_triggers.txt"), "un_case_standing_applies"),
        ]
        for parts, name in cases:
            with self.subTest(block=name):
                body = _block(_read(_path(*parts)), name)
                self.assertIn("un_membership_eligible = yes", body)
                self.assertNotIn("is_subject = no", body)

    def test_pariah_and_enrolment_ask_eligibility(self):
        je = _read(_path("common", "journal_entries", "je_united_nations.txt"))
        start = je.index("modifier:country_un_membership_obligation_bool")
        self.assertIn("un_membership_eligible = yes", je[start:start + 400])
        for mod in ("un_nonmember_pariah_modifier", "un_nonmember_pariah_strong_modifier"):
            with self.subTest(modifier=mod):
                add = je.index("add_modifier = { name = " + mod + " }")
                limit = je.rindex("un_tier_at_least", 0, add)
                self.assertIn("un_membership_eligible = yes", je[limit - 200:limit])


_TOP = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*\{", re.M)

# Blocks that name Article 19 for a reason other than taking a voice away.
_ARTICLE_19_ONLY = {
    "un_dues_vote_suspended",   # the definition
    "un_chamber_dues_lines",    # the dues display
    "un_pay_dues_button",       # an AI weight: settle once the vote is gone
}


def _script_files():
    for root in ("common", "events"):
        for dirpath, _dirs, files in os.walk(_path(root)):
            for f in files:
                if f.endswith(".txt"):
                    yield os.path.join(dirpath, f)


class RepresentationGateTests(unittest.TestCase):
    def test_every_article_19_gate_also_asks_suspension(self):
        missing = []
        for path in _script_files():
            text = _read(path)
            if "un_dues_vote_suspended" not in text:
                continue
            for m in _TOP.finditer(text):
                name = m.group(1)
                body = _block(text, name)
                if ("un_dues_vote_suspended" in body
                        and "un_representation_suspended" not in body
                        and name not in _ARTICLE_19_ONLY):
                    missing.append(f"{os.path.relpath(path, REPO)}: {name}")
        self.assertEqual(missing, [])

    def test_gates_without_article_19(self):
        cases = [
            (("common", "diplomatic_actions", "un_lobbying.txt"), "un_secure_commitment_action"),
            (("common", "scripted_triggers", "un_docket_triggers.txt"), "un_docket_loan_candidate"),
            (("common", "scripted_triggers", "un_docket_triggers.txt"), "un_docket_peacekeeping_power"),
            (("common", "scripted_triggers", "un_docket_triggers.txt"), "un_docket_aid_power"),
            (("common", "scripted_triggers", "un_mission_triggers.txt"), "un_mission_volunteer_eligible"),
            (("common", "scripted_triggers", "un_mission_triggers.txt"), "un_mission_slot_can_volunteer"),
            (("events", "un_vote_events.txt"), "un_vote.2"),
            (("events", "un_vote_events.txt"), "un_vote.3"),
        ]
        for parts, name in cases:
            with self.subTest(block=name):
                self.assertIn("un_representation_suspended", _block(_read(_path(*parts)), name))

    def test_lobbying_target_needs_a_vote(self):
        body = _block(_read(_path("common", "diplomatic_actions", "un_lobbying.txt")),
                      "un_secure_commitment_action")
        start = re.search(r"^\tpotential\s*=\s*\{", body, re.M).end()
        end = re.search(r"^\tpossible\s*=\s*\{", body, re.M).start()
        potential = body[start:end]
        self.assertIn("un_representation_suspended", potential)
        self.assertIn("un_dues_vote_suspended", potential)

    def test_headquarters_goes_only_to_represented_members(self):
        text = _read(_path("common", "scripted_effects", "un_hq_effects.txt"))
        for name in ("un_hq_assign_host", "un_hq_monthly_update"):
            with self.subTest(block=name):
                body = _block(text, name)
                self.assertIn("un_member_represented = yes", body)
                self.assertNotIn("has_modifier = un_member_modifier", body)


DUES = _path("common", "script_values", "un_dues_values.txt")


class DuesTests(unittest.TestCase):
    def test_assessment_reads_the_carried_gdp(self):
        text = _read(DUES)
        self.assertIn("un_dues_billed_to_overlord = yes", _block(text, "un_dues_assessed_gdp"))
        for name in ("un_dues_weekly_value", "un_dues_monthly_value"):
            with self.subTest(value=name):
                self.assertRegex(_block(text, name), r"value\s*=\s*un_dues_assessed_gdp")

    def test_pillar_and_budget_count_represented_members_once(self):
        text = _read(DUES)
        for name in ("un_members_gdp_value", "un_withholders_gdp_value", "un_budget_weekly_value"):
            with self.subTest(value=name):
                body = _block(text, name)
                self.assertIn("un_member_represented = yes", body)
                self.assertNotIn("has_modifier = un_member_modifier", body)

    def test_suspended_member_is_not_assessed(self):
        je = _read(_path("common", "journal_entries", "je_united_nations.txt"))
        call = je.index("un_dues_country_monthly_update = yes")
        self.assertIn("un_representation_suspended = yes", je[call - 500:call])
        buttons = _read(_path("common", "scripted_buttons", "un_buttons.txt"))
        for name in ("un_withhold_dues_button", "un_pay_dues_button"):
            with self.subTest(button=name):
                self.assertIn("un_representation_suspended", _block(buttons, name))


MODIFIERS = _path("common", "static_modifiers", "extra_modifiers.txt")
_FIELDS = {
    "country_improve_relations_speed_mult",
    "country_leverage_generation_add",
    "country_prestige_mult",
    "country_influence_mult",
    "country_defender_diplomatic_play_escalation_weekly_mult",
}


class PrivilegesTests(unittest.TestCase):
    def _fields(self, name):
        body = _block(_read(MODIFIERS), name)
        return {k for k in re.findall(r"^\s*(\w+)\s*=", body, re.M) if k != "icon"}

    def test_marker_has_no_effects(self):
        self.assertEqual(self._fields("un_member_modifier"), set())

    def test_privileges_carry_the_old_bonuses(self):
        self.assertEqual(self._fields("un_member_privileges_modifier"), _FIELDS)

    def test_every_join_path_grants_privileges_at_once(self):
        missing = []
        for path in _script_files():
            text = _read(path)
            for m in _TOP.finditer(text):
                body = _block(text, m.group(1))
                if re.search(r"add_modifier\s*=\s*\{\s*name\s*=\s*un_member_modifier\b", body) \
                        and "un_member_privileges_modifier" not in body:
                    missing.append(m.group(1))
        self.assertEqual(missing, [])

    def test_leaving_and_the_pulse(self):
        end = _block(_read(_path("common", "scripted_effects", "un_ladder_effects.txt")),
                     "un_membership_end_effect")
        self.assertIn("remove_modifier = un_member_privileges_modifier", end)
        je = _read(_path("common", "journal_entries", "je_united_nations.txt"))
        benefits = je.index("name = un_membership_benefits_modifier")
        self.assertIn("un_member_draws_benefits = yes", je[benefits - 600:benefits])
        self.assertGreaterEqual(je.count("un_member_privileges_modifier"), 3)


if __name__ == "__main__":
    unittest.main()
