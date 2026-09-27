# -*- coding: utf-8 -*-
"""The colonial empire across a revolution (PR #508).

A civil war's winner inherits the loser's variables but none of its modifiers,
and the mod's rule is that the winner continues the nation. So every country
modifier the colonial-empire system gives without a duration has a variable
record, and decol_repair_after_civil_war puts back each modifier whose record
the winner holds. The engine logs nothing when such a modifier silently
vanishes, so these tests pin the wiring: a new permanent modifier without a
record, or a record nobody clears, fails here.
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
    """The body of the first ``name = { ... }`` block at or after ``start``."""
    m = re.compile(r"(?<![\w.:$])" + re.escape(name) + r"\s*=\s*\{").search(text, start)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


EFFECTS = _read("common", "scripted_effects", "decolonization.txt")
EVENTS = _read("events", "decolonization_events.txt")
DECISIONS = _read("common", "decisions", "extra_decisions.txt")
JE = _read("common", "journal_entries", "je_colonial_empire.txt")
CIVIL_WAR = _read("common", "on_actions", "te_civil_war_on_actions.txt")
EXTRA_ON_ACTIONS = _read("common", "on_actions", "extra_on_actions.txt")

# Permanent country modifiers and the variable that records each.
PERMANENT = {
    "colonial_empire_solidified_modifier": "colonial_empire_solidified_modifier_held",
    "commonwealth_path_modifier": "commonwealth_path_modifier_held",
    "iron_fist_path_modifier": "iron_fist_path_modifier_held",
    "quiet_assimilation_path_modifier": "quiet_assimilation_path_modifier_held",
    "imperial_federation_modifier": "imperial_federation_taken",
    "mandate_system_modifier": "mandate_system_taken",
}
# The running programmes: (modifier, the effect that enables it, the one that removes it).
PROGRAMMES = (
    ("colonial_development_investment_modifier",
     "colonial_empire_effect_invest", "colonial_empire_effect_remove_invest"),
    ("colonial_military_garrison_modifier",
     "colonial_empire_effect_garrison", "colonial_empire_effect_remove_garrison"),
    ("colonial_cultural_assimilation_modifier",
     "colonial_empire_effect_assimilation", "colonial_empire_effect_remove_assimilation"),
)
# Undated modifiers that need no record, and why.
NOT_RECORDED = {
    # re-added by the entry's monthly pulse whenever the Invest programme is on
    "colonial_development_investment_expense_modifier",
    # the entry's band modifiers: on the entry itself, re-applied every month
    "colonial_empire_crumbling_modifier",
    "colonial_empire_under_pressure_modifier",
    "colonial_empire_strained_modifier",
    "colonial_empire_stable_modifier",
    # on subjects and movements, re-applied every month by the entry
    "colonial_overlord_collapsing_subject_ld_modifier",
    "colonial_overlord_crumbling_subject_ld_modifier",
    "colonial_overlord_strained_subject_ld_modifier",
    "colonial_crumbling_movement_radicalism",
    "colonial_pressure_movement_radicalism",
}


def _undated_add_modifiers(text):
    """Names added by an add_modifier with no duration, or days = -1."""
    names = set()
    for m in re.finditer(r"\badd_modifier\s*=\s*\{", text):
        body = text[m.end():_close(text, m.end() - 1)]
        name = re.search(r"\bname\s*=\s*([\w$]+)", body)
        if name is None or "$" in name.group(1):
            continue
        dur = re.search(r"\b(days|months|years)\s*=\s*(\S+)", body)
        if dur is None or (dur.group(1) == "days" and dur.group(2) == "-1"):
            names.add(name.group(1))
    return names


def _colonial_decisions():
    return "".join(_block(DECISIONS, d) for d in (
        "imperial_federation_act_iron_fist",
        "imperial_federation_act_civilizing_mission",
        "mandate_system_decision"))


class CoverageTests(unittest.TestCase):
    def test_every_undated_colonial_modifier_is_recorded_or_exempt(self):
        found = (_undated_add_modifiers(EFFECTS) | _undated_add_modifiers(EVENTS)
                 | _undated_add_modifiers(JE) | _undated_add_modifiers(_colonial_decisions()))
        # colonial_empire_solidified_modifier is also the entry's top band
        # modifier (je_colonial_empire.txt); the country copy is the recorded one.
        covered = set(PERMANENT) | {p[0] for p in PROGRAMMES} | NOT_RECORDED
        missing = sorted(found - covered)
        self.assertEqual(missing, [],
                         "undated colonial modifiers with no record: add them to the "
                         "decolonization.txt sync (and PERMANENT here) or to NOT_RECORDED")

    def test_sync_lists_every_permanent_modifier(self):
        sync = _block(EFFECTS, "decol_sync_permanent_modifiers")
        pairs = dict(re.findall(
            r"decol_sync_permanent_modifier\s*=\s*\{\s*MODIFIER\s*=\s*(\w+)\s+RECORD\s*=\s*(\w+)\s*\}",
            sync))
        self.assertEqual(pairs, PERMANENT)

    def test_programme_sync_lists_every_programme(self):
        sync = _block(EFFECTS, "decol_sync_programmes")
        self.assertIn("has_journal_entry = je_colonial_empire", _block(sync, "limit"))
        listed = re.findall(r"decol_sync_programme\s*=\s*\{\s*MODIFIER\s*=\s*(\w+)\s*\}", sync)
        self.assertEqual(sorted(listed), sorted(p[0] for p in PROGRAMMES))


class RecordTests(unittest.TestCase):
    def test_ending_rewards_are_granted_with_their_record(self):
        # A bare days = -1 grant would skip the record.
        for name, record in PERMANENT.items():
            if not record.endswith("_held"):
                continue
            with self.subTest(modifier=name):
                bare = re.search(r"add_modifier\s*=\s*\{\s*name\s*=\s*" + name
                                 + r"\s+days\s*=\s*-1\s*\}", EVENTS)
                self.assertIsNone(bare, f"{name} is granted without decol_grant_permanent_modifier")
                self.assertRegex(EVENTS, r"decol_grant_permanent_modifier\s*=\s*\{\s*MODIFIER\s*=\s*"
                                 + name + r"\s*\}")
        grant = _block(EFFECTS, "decol_grant_permanent_modifier")
        self.assertIn("name = $MODIFIER$_held", grant)
        self.assertRegex(grant, r"days\s*=\s*-1")

    def test_decisions_set_their_record(self):
        for decision, record in (("imperial_federation_act_iron_fist", "imperial_federation_taken"),
                                 ("imperial_federation_act_civilizing_mission", "imperial_federation_taken"),
                                 ("mandate_system_decision", "mandate_system_taken")):
            with self.subTest(decision=decision):
                self.assertRegex(_block(_block(DECISIONS, decision), "when_taken"),
                                 r"set_variable\s*=\s*" + record + r"\b")

    def test_programme_records_follow_the_toggles_and_the_entry(self):
        cleanup = _block(EFFECTS, "colonial_empire_je_cleanup_effect")
        for modifier, on, off in PROGRAMMES:
            with self.subTest(programme=modifier):
                self.assertRegex(_block(EFFECTS, on),
                                 r"set_variable\s*=\s*\{\s*name\s*=\s*" + modifier + r"_held\b")
                self.assertRegex(_block(EFFECTS, off),
                                 r"remove_variable\s*=\s*" + modifier + r"_held\b")
                self.assertRegex(cleanup, r"remove_variable\s*=\s*" + modifier + r"_held\b")


class RepairTests(unittest.TestCase):
    def test_the_civil_war_hook_runs_the_repair(self):
        self.assertIn("decol_repair_after_civil_war = yes", _block(CIVIL_WAR, "te_civil_war_on_won"))
        repair = _block(EFFECTS, "decol_repair_after_civil_war")
        self.assertIn("decol_sync_permanent_modifiers = yes", repair)
        self.assertIn("decol_sync_programmes = yes", repair)

    def test_the_repair_only_adds(self):
        # Stateless and add-only, so a loyalist winner sees no change.
        for effect in ("decol_sync_permanent_modifier", "decol_sync_programme",
                       "decol_repair_after_civil_war"):
            with self.subTest(effect=effect):
                body = _block(EFFECTS, effect)
                self.assertNotIn("remove_modifier", body)
                self.assertNotIn("remove_variable", body)

    def test_backstop_pulses(self):
        self.assertIn("decol_sync_programmes = yes",
                      _block(_block(JE, "on_monthly_pulse"), "effect"))
        self.assertIn("decol_permanent_modifier_sync_on_action",
                      _block(EXTRA_ON_ACTIONS, "on_yearly_pulse_country"))
        self.assertIn("decol_sync_permanent_modifiers = yes",
                      _block(EXTRA_ON_ACTIONS, "decol_permanent_modifier_sync_on_action"))


if __name__ == "__main__":
    unittest.main()
