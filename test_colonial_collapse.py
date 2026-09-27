# -*- coding: utf-8 -*-
"""Colonial collapse's gates and guards (PR #508, owner rulings of 2026-09-26).

Collapse annexes or decentralizes whole countries, so its guards are pinned
here: nothing in the engine reports a guard that went missing, only a country
that vanished when it should not have.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _block(text, name, start=0):
    m = re.compile(r"(?<![\w.:$])" + re.escape(name) + r"\s*=\s*\{").search(text, start)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


COLLAPSE = _block(_read("common", "scripted_effects", "colonial_collapse_effects.txt"),
                  "colonial_collapse_effect")
LIMIT = _block(COLLAPSE, "limit")
TRIGGERS = _read("common", "scripted_triggers", "colonial_empire_triggers.txt")
EXTRA_ON_ACTIONS = _read("common", "on_actions", "extra_on_actions.txt")
CIVIL_WAR = _read("common", "on_actions", "te_civil_war_on_actions.txt")
EVENTS = _read("events", "decolonization_events.txt")


class LimitTests(unittest.TestCase):
    def test_gates(self):
        self.assertIn("has_game_rule = decolonization_enabled", LIMIT)
        self.assertIn("decol_era_begun = yes", LIMIT)
        self.assertIn("is_player = no", LIMIT)
        self.assertRegex(LIMIT, r"NOT\s*=\s*\{\s*any_subject_or_below\s*=\s*\{\s*always\s*=\s*yes\s*\}\s*\}")
        self.assertNotRegex(LIMIT, r"always\s*=\s*no")

    def test_twenty_years_grace_from_either_variable(self):
        for var in ("recently_decolonized", "decol_collapse_grace"):
            with self.subTest(var=var):
                self.assertRegex(LIMIT, r"NOT\s*=\s*\{\s*has_variable\s*=\s*" + var + r"\s*\}")

    def test_bloc_and_treaty_guard_both_branches(self):
        # One trigger, in the shared limit, so the branches cannot drift.
        self.assertIn("colonial_collapse_unattached = yes", LIMIT)
        guard = _block(TRIGGERS, "colonial_collapse_unattached")
        self.assertIn("is_in_power_bloc = no", guard)
        self.assertRegex(guard, r"NOT\s*=\s*\{\s*any_scope_treaty\s*=\s*\{\s*always\s*=\s*yes\s*\}\s*\}")
        self.assertNotIn("is_in_power_bloc", COLLAPSE)
        self.assertNotIn("any_scope_treaty", COLLAPSE)


class BranchTests(unittest.TestCase):
    def test_absorber_is_an_ai_country_at_peace(self):
        search = _block(COLLAPSE, "random_neighbouring_state")
        owner = _block(_block(search, "limit"), "owner")
        for cond in ("is_player = no", "is_at_war = no", "is_subject = no"):
            with self.subTest(cond=cond):
                self.assertIn(cond, owner)

    def test_decentralize_needs_no_company_and_no_warheads(self):
        branch = _block(COLLAPSE, "else_if")
        self.assertIn("set_country_type = decentralized", branch)
        guard = _block(branch, "limit")
        self.assertIn("nd_is_armed = no", guard)
        self.assertRegex(guard, r"NOT\s*=\s*\{\s*any_company\s*=\s*\{\s*always\s*=\s*yes\s*\}\s*\}")

    def test_notice_before_annexation(self):
        branch = _block(COLLAPSE, "if", COLLAPSE.index("exists = scope:absorbing_country") - 40)
        self.assertLess(branch.index("colonial_territory_absorbed_notice"),
                        branch.index("annex = scope:collapsing_country"))


class GraceTests(unittest.TestCase):
    def test_grace_is_set_on_independence_and_a_won_secession(self):
        on_become = _block(EXTRA_ON_ACTIONS, "on_become_independent")
        self.assertIn("decol_collapse_grace_on_action", on_become)
        self.assertRegex(_block(EXTRA_ON_ACTIONS, "decol_collapse_grace_on_action"),
                         r"set_variable\s*=\s*\{\s*name\s*=\s*decol_collapse_grace\s+days\s*=\s*7300\s*\}")
        secession = _block(CIVIL_WAR, "te_civil_war_on_secession_end")
        self.assertRegex(secession, r"set_variable\s*=\s*\{\s*name\s*=\s*decol_collapse_grace\s+days\s*=\s*7300\s*\}")

    def test_grace_opens_no_event(self):
        # The post-independence events key on recently_decolonized alone.
        self.assertNotIn("decol_collapse_grace", EVENTS)
        self.assertNotIn("decol_collapse_grace", _block(EXTRA_ON_ACTIONS, "decolonization_events_on_action"))


if __name__ == "__main__":
    unittest.main()
