# -*- coding: utf-8 -*-
"""The colonial empire across a revolution (PR #508).

A civil war's winner inherits the loser's variables but none of its modifiers,
and the mod's rule is that the winner continues the nation. So every country
modifier the colonial-empire system gives without a duration has a variable
record, and decol_repair_after_civil_war puts back each modifier whose record
the winner holds. The engine logs nothing when such a modifier silently
vanishes, so these tests pin the wiring: a new permanent modifier without a
record, or a record nobody clears, fails here.

The three programmes are no longer country modifiers: since 1.15 the entry
declares them from their level variables (scaling_modifiers_while_active,
test_colonial_scaling_modifiers.py), the winner inherits the levels, and the
repair has nothing to rebuild for them (#1404).
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
# The running programmes: (modifier, its level variable (the programme's only
# state, which the winner inherits), the step cores that raise and lower it).
PROGRAMMES = (
    ("colonial_development_investment_modifier", "colonial_invest_level",
     "colonial_programme_invest_up", "colonial_programme_invest_down"),
    ("colonial_military_garrison_modifier", "colonial_garrison_level",
     "colonial_programme_garrison_up", "colonial_programme_garrison_down"),
    ("colonial_cultural_assimilation_modifier", "colonial_assim_level",
     "colonial_programme_assimilation_up", "colonial_programme_assimilation_down"),
)
# Undated modifiers that need no record, and why.
NOT_RECORDED = {
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
        # The programmes are declared, never added (no entry in `covered`).
        covered = set(PERMANENT) | NOT_RECORDED
        missing = sorted(found - covered)
        self.assertEqual(missing, [],
                         "undated colonial modifiers with no record: add them to the "
                         "decolonization.txt sync (and PERMANENT here) or to NOT_RECORDED")

    def test_sync_lists_every_permanent_modifier(self):
        sync = _block(EFFECTS, "decol_sync_permanent_modifiers")
        call = r"\s*=\s*\{\s*MODIFIER\s*=\s*(\w+)\s+RECORD\s*=\s*(\w+)\s*\}"
        pairs = dict(re.findall(r"decol_sync_permanent_modifier" + call, sync))
        # Solidified is synced in halves (test_solidified_backfill_waits_for_no_entry).
        backfilled = dict(re.findall(r"decol_backfill_permanent_record" + call, sync))
        restored = dict(re.findall(r"decol_restore_permanent_modifier" + call, sync))
        self.assertEqual(backfilled, restored)
        self.assertFalse(set(pairs) & set(restored))
        self.assertEqual({**pairs, **restored}, PERMANENT)

    def test_solidified_backfill_waits_for_no_entry(self):
        # colonial_empire_solidified_modifier is also the entry's top band
        # modifier (on je:je_colonial_empire). Its record may be backfilled only
        # while no entry runs, so a country-scope has_modifier that saw the band
        # modifier could never mint the permanent reward.
        sync = _block(EFFECTS, "decol_sync_permanent_modifiers")
        pos = sync.index("decol_backfill_permanent_record = { MODIFIER = colonial_empire_solidified_modifier")
        guards = []
        for m in re.finditer(r"\bif\s*=\s*\{", sync):
            end = _close(sync, m.end() - 1)
            if m.start() < pos < end:
                guards.append(_block(sync[m.start():end + 1], "limit"))
        self.assertTrue(any(re.search(r"NOT\s*=\s*\{\s*has_journal_entry\s*=\s*je_colonial_empire\s*\}", g)
                            for g in guards),
                        "the Solidified backfill is not gated on the entry being inactive")
        self.assertNotRegex(sync, r"decol_sync_permanent_modifier\s*=\s*\{\s*MODIFIER\s*=\s*"
                                  r"colonial_empire_solidified_modifier\b")

    def test_the_programmes_have_no_rebuild(self):
        # The entry declares them; a rebuild beside the declaration would double
        # them (an add_modifier of a declared key stacks with it).
        for name in ("decol_sync_programmes", "decol_migrate_programme", "decol_migrate_programmes",
                     "colonial_programmes_refresh_modifiers", "colonial_programme_apply_modifier"):
            with self.subTest(effect=name):
                self.assertNotRegex(EFFECTS + JE, r"(?<![\w.:$])" + name + r"\b")


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

    def test_the_pulse_reads_programme_levels(self):
        # has_modifier can't see a declared modifier; the level variables are
        # the programmes' state. So the month counters and the assimilation
        # disruption read the levels.
        pulse = _block(_block(JE, "on_monthly_pulse"), "effect")
        for modifier, level, _up, _down in PROGRAMMES:
            with self.subTest(programme=modifier):
                self.assertNotRegex(pulse, r"\b" + modifier + r"\b")
                self.assertNotRegex(pulse, modifier + r"_held\b")
        for value in ("colonial_invest_level_value", "colonial_garrison_level_value",
                      "colonial_assim_level_value"):
            self.assertIn(value, pulse)

    def test_the_ai_steps_cores_and_a_player_steps_through_the_widget(self):
        # The AI's review (from the pulse) calls the cores; a player's effect is
        # the core plus colonial_programme_after_step, the widget's snapshot.
        review = _block(EFFECTS, "colonial_ai_review_programmes")
        self.assertNotRegex(review, r"colonial_empire_effect_\w+")
        self.assertNotIn("colonial_programme_after_step", review)
        for _modifier, _level, up, down in PROGRAMMES:
            for core in (up, down):
                with self.subTest(core=core):
                    self.assertIn(core + " = yes", review)
                    self.assertNotIn("colonial_programme_after_step", _block(EFFECTS, core))
                    player = core.replace("colonial_programme_", "colonial_empire_effect_")
                    body = _block(EFFECTS, player)
                    self.assertIn(core + " = yes", body)
                    self.assertIn("colonial_programme_after_step = yes", body)
        self.assertIn("colonial_empire_refresh_display = yes", _block(EFFECTS, "colonial_programme_after_step"))

    def test_programme_levels_follow_the_steps_and_the_entry(self):
        cleanup = _block(EFFECTS, "colonial_empire_je_cleanup_effect")
        for modifier, level, up, down in PROGRAMMES:
            with self.subTest(programme=modifier):
                self.assertRegex(_block(EFFECTS, up),
                                 r"change_variable\s*=\s*\{\s*name\s*=\s*" + level + r"\s+add\s*=\s*1\s*\}")
                self.assertRegex(_block(EFFECTS, down),
                                 r"change_variable\s*=\s*\{\s*name\s*=\s*" + level + r"\s+subtract\s*=\s*1\s*\}")
                for core in (up, down):
                    self.assertRegex(_block(EFFECTS, core),
                                     r"clamp_variable\s*=\s*\{\s*name\s*=\s*" + level
                                     + r"\s+min\s*=\s*0\s+max\s*=\s*colonial_programme_max_level\s*\}")
                self.assertRegex(cleanup, r"remove_variable\s*=\s*" + level + r"\b")

    def test_a_missing_level_starts_from_the_guarded_value(self):
        # A country that never stepped a programme holds no level variable; each
        # core starts it from the guarded wrapper (0) before the change.
        values = _read("common", "script_values", "colonial_empire_values.txt")
        for modifier, level, up, down in PROGRAMMES:
            with self.subTest(programme=modifier):
                self.assertIn("has_variable = " + level, _block(values, level + "_value"))
                for core in (up, down):
                    self.assertRegex(_block(EFFECTS, core), r"set_variable\s*=\s*\{\s*name\s*=\s*" + level
                                     + r"\s+value\s*=\s*" + level + r"_value\s*\}")


class AiReviewTests(unittest.TestCase):
    VALUES = _read("common", "script_values", "colonial_empire_values.txt")

    def test_a_full_bar_keeps_a_margin(self):
        # At 100 the ceiling is a positive margin, not 0: trimmed to 0, the
        # change would drop the bar off 100 at the first war and restart the
        # 60-month completion count.
        ceiling = _block(self.VALUES, "colonial_ai_programme_ceiling")
        self.assertIn("colonial_stability_bar_at_least = { N = 100 }", ceiling)
        self.assertIn("value = colonial_ai_full_bar_margin", ceiling)
        margin = re.search(r"(?m)^colonial_ai_full_bar_margin\s*=\s*([\d.]+)", self.VALUES)
        self.assertTrue(margin and float(margin.group(1)) > 0)

    def test_raise_weights_use_value(self):
        # `add = <named script value>` in a weight modifier logs "Malformed token".
        review = _block(EFFECTS, "colonial_ai_review_programmes")
        weights = re.findall(r"modifier\s*=\s*\{\s*(\w+)\s*=\s*(colonial_ai_\w+_raise_weight)\s*\}", review)
        self.assertEqual(sorted(w for _, w in weights),
                         ["colonial_ai_assim_raise_weight", "colonial_ai_garrison_raise_weight",
                          "colonial_ai_invest_raise_weight"])
        self.assertEqual({op for op, _ in weights}, {"value"})


class RepairTests(unittest.TestCase):
    def test_the_civil_war_hook_runs_the_repair(self):
        self.assertIn("decol_repair_after_civil_war = yes", _block(CIVIL_WAR, "te_civil_war_on_won"))
        repair = _block(EFFECTS, "decol_repair_after_civil_war")
        self.assertIn("decol_sync_permanent_modifiers = yes", repair)
        # The programmes ride the inherited entry's declarations (#1404).
        self.assertNotIn("programmes", repair)

    def test_the_repair_only_adds(self):
        # Stateless and add-only, so a loyalist winner sees no change.
        for effect in ("decol_backfill_permanent_record", "decol_restore_permanent_modifier",
                       "decol_sync_permanent_modifier", "decol_sync_permanent_modifiers",
                       "decol_repair_after_civil_war"):
            with self.subTest(effect=effect):
                body = _block(EFFECTS, effect)
                self.assertNotIn("remove_modifier", body)
                self.assertNotIn("remove_variable", body)

    def test_backstop_pulses(self):
        self.assertIn("decol_permanent_modifier_sync_on_action",
                      _block(EXTRA_ON_ACTIONS, "on_yearly_pulse_country"))
        self.assertIn("decol_sync_permanent_modifiers = yes",
                      _block(EXTRA_ON_ACTIONS, "decol_permanent_modifier_sync_on_action"))


if __name__ == "__main__":
    unittest.main()
