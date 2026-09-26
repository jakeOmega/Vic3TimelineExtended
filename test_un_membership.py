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


if __name__ == "__main__":
    unittest.main()
