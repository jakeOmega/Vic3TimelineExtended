# -*- coding: utf-8 -*-
"""A Space Race milestone starts again after a programme loss.

A lowered Space Program method or a lost building fails every milestone the
launch complex can no longer carry: each milestone's failure outcome
(je_space_race.txt) concludes its journal entry. The engine deletes a concluded
record three days later and never activates the type again
(docs/guides/scripting_best_practices.md, "A finished record is deleted"), so
the milestone never came back. A monthly pass, sr_reentry_monthly
(common/scripted_effects/space_race_effects.txt), adds it back with
add_journal_entry once the country has been due it (sr_reentry_due_<m>,
common/scripted_triggers/space_race_triggers.txt) for a whole month. The
progress lost at the failure stays lost (owner, 2026-11-06).

Pinned here:
- the pass covers exactly the entries whose failure outcome runs the failure
  cleanup, and each sr_reentry_due_<m> restates its entry's
  is_shown_when_inactive and possible word for word (add_journal_entry skips
  both), after the guards the add needs, the record tests first;
- the pass runs for players and AI alike, monthly, after the inactive-milestone
  cleanup, while the race is on; it waits a month, adds, and clears its mark
  when the country stops being due;
- its two self-checks (sr_reentry: does the add bring a finished type back?
  sr_closed_record: is the record really gone for good?) read last month's add
  before it can add again, judge only a country whose own milestone closed on a
  programme loss, read "running" from sr_active_<m>, log each verdict once a
  game, and are in the play-test list with their fallbacks;
- the failure cleanup marks the closure and still wipes the milestone (the
  owner's ruling); a revolution's winner drops the closed marks.
"""

import os
import re
import unittest

from je_test_helpers import entry_text, field, old_block

REPO = os.path.dirname(os.path.abspath(__file__))


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _read(*parts):
    return re.sub(r"#[^\n]*", "", _raw(*parts))


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


def _defn(text, name):
    """The body of the top-level definition `name = { ... }`, not a call of it."""
    m = re.compile(r"^" + re.escape(name) + r"\s*=\s*\{", re.M).search(text)
    if m is None:
        raise AssertionError(f"no definition of {name}")
    return text[m.end():_close(text, m.end() - 1)]


def _norm(text):
    """Whitespace-insensitive form of a script fragment."""
    return " ".join(text.split())


def _branch(text, opener, kind="if"):
    """The body of the first `kind` block (`if` or `else_if`) whose limit starts with `opener`."""
    for m in re.finditer(r"(?<![\w.:$])" + kind + r"\s*=\s*\{", text):
        body = text[m.end():_close(text, m.end() - 1)]
        limit = _block(body, "limit")
        if _norm(limit).startswith(_norm(opener)):
            return body
    raise AssertionError(f"no branch on {opener!r}")


JE_RAW = _raw("common", "journal_entries", "je_space_race.txt")
TRIGGERS = _read("common", "scripted_triggers", "space_race_triggers.txt")
EFFECTS = _read("common", "scripted_effects", "space_race_effects.txt")
PASS = _defn(EFFECTS, "sr_reentry_monthly")
BASE = _defn(EFFECTS, "sr_reentry_milestone")
ON_ACTIONS = _read("common", "on_actions", "space_race_on_actions.txt")
PLAYTEST = _raw("docs", "testing", "space-race-playtest.md")

MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "mars_landing", "interstellar_probe",
              "solar_colonization")


def _entry(milestone):
    return entry_text(JE_RAW, f"je_space_race_{milestone}")


class CoverageTests(unittest.TestCase):
    def test_the_pass_covers_every_entry_a_programme_loss_closes(self):
        closed = re.findall(r"sr_cleanup_milestone_variables_effect = \{ MILESTONE = (\w+) \}",
                            re.sub(r"#[^\n]*", "", JE_RAW))
        self.assertEqual(sorted(closed), sorted(MILESTONES))
        self.assertEqual(re.findall(r"sr_reentry_milestone = \{ MILESTONE = (\w+)\s*\}", PASS), list(MILESTONES))
        self.assertEqual(sorted(re.findall(r"^sr_reentry_due_(\w+) = \{", TRIGGERS, re.M)), sorted(MILESTONES))

    def test_each_failure_outcome_closes_through_the_cleanup(self):
        for m in MILESTONES:
            with self.subTest(milestone=m):
                entry = _entry(m)
                self.assertRegex(_norm(old_block(entry, "fail")),
                                 r"NOT = \{ modifier:country_sr_\w+_program_bool = yes \}")
                self.assertIn(f"sr_cleanup_milestone_variables_effect = {{ MILESTONE = {m} }}",
                              old_block(entry, "on_fail"))


class DueTests(unittest.TestCase):
    def test_restates_is_shown_when_inactive_word_for_word(self):
        for m in MILESTONES:
            with self.subTest(milestone=m):
                shown = _norm(field(_entry(m), "is_shown_when_inactive"))
                self.assertTrue(shown)
                self.assertIn(shown, _norm(_defn(TRIGGERS, f"sr_reentry_due_{m}")))

    def test_restates_possible_word_for_word(self):
        for m in MILESTONES:
            with self.subTest(milestone=m):
                possible = _norm(field(_entry(m), "possible"))
                self.assertIn("program_bool = yes", possible)
                self.assertIn(possible, _norm(_defn(TRIGGERS, f"sr_reentry_due_{m}")))

    def test_a_completed_milestone_is_never_due(self):
        # Through the restated possible: the single-goal milestones require the
        # absence of their completion.
        for m in MILESTONES[:-1]:
            with self.subTest(milestone=m):
                self.assertIn(f"NOT = {{ has_variable = sr_completed_{m} }}", field(_entry(m), "possible"))

    def test_the_guards_the_add_needs_come_first(self):
        guards = ("NOT = {{ has_journal_entry = je_space_race_{m} }}",
                  "NOT = {{ has_inactive_journal_entry = je_space_race_{m} }}",
                  "NOT = {{ is_country_type = decentralized }}",
                  "is_revolutionary = no")
        for m in MILESTONES:
            with self.subTest(milestone=m):
                due = _norm(_defn(TRIGGERS, f"sr_reentry_due_{m}"))
                # Every country holds an inactive record of each milestone until
                # it concludes, so the record tests end the trigger for nearly
                # every country before anything else is read.
                self.assertTrue(due.startswith(" ".join(g.format(m=m) for g in guards)), due[:200])


class PassTests(unittest.TestCase):
    def test_monthly_after_the_inactive_cleanup_while_the_race_is_on(self):
        self.assertRegex(ON_ACTIONS, r"on_monthly_pulse_country\s*=\s*\{\s*on_actions\s*=\s*\{\s*space_race_on_action")
        monthly = _defn(ON_ACTIONS, "space_race_on_action")
        self.assertEqual(monthly.count("sr_reentry_monthly = yes"), 1)
        self.assertLess(monthly.index("sr_cleanup_inactive_space_race_milestones = yes"),
                        monthly.index("sr_reentry_monthly = yes"))
        self.assertRegex(_norm(monthly), r"if = \{ limit = \{ sr_space_race_on = yes \} sr_reentry_monthly = yes \}")

    def test_for_players_and_ai_alike(self):
        for name, text in [("pass", PASS), ("base", BASE)] + [
                (m, _defn(TRIGGERS, f"sr_reentry_due_{m}")) for m in MILESTONES]:
            for gate in ("is_ai", "is_player", "is_local_player", "sr_ai_should_participate"):
                self.assertNotIn(gate, text, f"{gate} in {name}")

    def test_adds_only_after_a_whole_month(self):
        due = _branch(BASE, "sr_reentry_due_$MILESTONE$ = yes")
        waited = _branch(due, "var:sr_reentry_waiting_$MILESTONE$ ?= scope:sr_reentry_country")
        self.assertIn("add_journal_entry = { type = je_space_race_$MILESTONE$ }", _norm(waited))
        self.assertIn("remove_variable = sr_reentry_waiting_$MILESTONE$", waited)
        self.assertRegex(due, r"\}\s*else = \{\s*set_variable = \{ name = sr_reentry_waiting_\$MILESTONE\$ "
                              r"value = scope:sr_reentry_country \}\s*\}")
        # The only add in the pass is the one behind the month's mark.
        self.assertEqual(len(re.findall(r"add_journal_entry\s*=\s*\{", BASE + PASS)), 1)

    def test_the_mark_goes_when_the_country_stops_being_due(self):
        cleared = _branch(BASE, "has_variable = sr_reentry_waiting_$MILESTONE$", kind="else_if")
        self.assertIn("remove_variable = sr_reentry_waiting_$MILESTONE$", cleared)
        self.assertNotIn("add_journal_entry", cleared)
        self.assertRegex(BASE, r"\}\s*else_if = \{\s*limit = \{ has_variable = sr_reentry_waiting_\$MILESTONE\$ \}")

    def test_the_marks_name_the_country_itself(self):
        self.assertTrue(PASS.lstrip().startswith("save_scope_as = sr_reentry_country"))
        self.assertIn("set_variable = { name = sr_reentry_added_$MILESTONE$ value = scope:sr_reentry_country }",
                      BASE)


class SelfCheckTests(unittest.TestCase):
    def setUp(self):
        self.check = _branch(BASE, "has_variable = sr_reentry_added_$MILESTONE$")

    def test_last_months_add_is_read_before_this_months(self):
        first = re.search(r"(?<![\w.:$])if\s*=\s*\{", BASE)
        self.assertIn(self.check, BASE[first.end():_close(BASE, first.end() - 1)])
        add = re.search(r"add_journal_entry\s*=\s*\{", BASE)
        self.assertLess(BASE.index("limit = { has_variable = sr_reentry_added_$MILESTONE$ }"), add.start())
        self.assertNotRegex(self.check, r"add_journal_entry\s*=\s*\{")
        # Read once, then gone, whatever the verdict.
        verdicts = _branch(self.check, "var:sr_reentry_added_$MILESTONE$ ?= scope:sr_reentry_country")
        after = self.check[self.check.index(verdicts) + len(verdicts):]
        self.assertIn("remove_variable = sr_reentry_added_$MILESTONE$", after)

    def test_judged_only_for_the_countrys_own_closed_milestone(self):
        verdicts = _branch(self.check, "var:sr_reentry_added_$MILESTONE$ ?= scope:sr_reentry_country "
                                       "var:sr_closed_by_loss_$MILESTONE$ ?= scope:sr_reentry_country")
        ok = _branch(verdicts, "has_journal_entry = je_space_race_$MILESTONE$ has_variable = sr_active_$MILESTONE$")
        self.assertIn("TE_SELF_CHECK OK sr_reentry", ok)
        self.assertIn("remove_variable = sr_closed_by_loss_$MILESTONE$", ok)
        broken = _branch(verdicts, "sr_reentry_due_$MILESTONE$ = yes", kind="else_if")
        self.assertIn("TE_SELF_CHECK BROKEN sr_reentry", broken)
        self.assertNotIn("TE_SELF_CHECK OK", broken)

    def test_the_engines_own_return(self):
        back = _branch(BASE, "var:sr_closed_by_loss_$MILESTONE$ ?= scope:sr_reentry_country "
                             "has_journal_entry = je_space_race_$MILESTONE$ has_variable = sr_active_$MILESTONE$",
                       kind="else_if")
        self.assertIn("TE_SELF_CHECK BROKEN sr_closed_record", back)
        self.assertIn("remove_variable = sr_closed_by_loss_$MILESTONE$", back)
        # The else of last month's add: a milestone the pass added is not the engine's.
        self.assertRegex(BASE, r"remove_variable = sr_reentry_added_\$MILESTONE\$\s*\}\s*else_if = \{\s*limit = \{\s*"
                               r"var:sr_closed_by_loss_\$MILESTONE\$")

    def test_the_closed_record_is_confirmed_at_the_add(self):
        waited = _branch(_branch(BASE, "sr_reentry_due_$MILESTONE$ = yes"),
                         "var:sr_reentry_waiting_$MILESTONE$ ?= scope:sr_reentry_country")
        noted = _branch(waited, "var:sr_closed_by_loss_$MILESTONE$ ?= scope:sr_reentry_country")
        self.assertIn("TE_SELF_CHECK OK sr_closed_record", noted)
        self.assertLess(waited.index("TE_SELF_CHECK OK sr_closed_record"), waited.index("add_journal_entry"))

    def test_four_verdicts_each_once_a_game(self):
        lines = re.findall(r'debug_log = "(TE_SELF_CHECK [^"]*)"', BASE)
        self.assertEqual(sorted(re.match(r"TE_SELF_CHECK (\w+) (\w+) ", line).groups() for line in lines),
                         [("BROKEN", "sr_closed_record"), ("BROKEN", "sr_reentry"),
                          ("OK", "sr_closed_record"), ("OK", "sr_reentry")])
        for verdict, check in (("ok", "reentry"), ("broken", "reentry"),
                               ("ok", "closed_record"), ("broken", "closed_record")):
            flag = f"sr_{check}_{verdict}_logged"
            with self.subTest(flag=flag):
                self.assertEqual(BASE.count(f"NOT = {{ has_global_variable = {flag} }}"), 1)
                self.assertRegex(BASE, r"set_global_variable = \{ name = " + flag + r" value = yes \}\s*"
                                       r'debug_log = "TE_SELF_CHECK ' + verdict.upper())
        for line in re.findall(r'debug_log = "([^"]*)"', BASE):
            self.assertIn("milestone=$MILESTONE$", line)
            self.assertIn("[TimeKeeper.GetCurrentDate.GetString]", line)
            self.assertIn("[THIS.GetCountry.GetTagName]", line)
            self.assertNotIn("GetTag]", line)

    def test_in_the_playtest_list_with_their_fallbacks(self):
        for check in ("sr_reentry", "sr_closed_record"):
            with self.subTest(check=check):
                rows = [line for line in PLAYTEST.splitlines() if line.startswith(f"| `{check}` |")]
                self.assertEqual(len(rows), 1)
        reentry = [line for line in PLAYTEST.splitlines() if line.startswith("| `sr_reentry` |")][0]
        self.assertIn("deactivate", reentry)
        self.assertIn("failure outcome", reentry)


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.cleanup = _defn(EFFECTS, "sr_cleanup_milestone_variables_effect")

    def test_the_failure_cleanup_marks_the_closure_naming_the_country(self):
        self.assertIn("save_temporary_scope_as = sr_closing_country", self.cleanup)
        self.assertIn("set_variable = { name = sr_closed_by_loss_$MILESTONE$ value = scope:sr_closing_country }",
                      self.cleanup)
        self.assertLess(self.cleanup.index("save_temporary_scope_as"), self.cleanup.index("sr_closed_by_loss_"))
        # An add that closes again before it is judged gives no verdict.
        self.assertIn("if = { limit = { has_variable = sr_reentry_added_$MILESTONE$ } "
                      "remove_variable = sr_reentry_added_$MILESTONE$ }", _norm(self.cleanup))
        # Only the failure cleanup sets the mark.
        everything = EFFECTS + TRIGGERS + ON_ACTIONS + re.sub(r"#[^\n]*", "", JE_RAW)
        self.assertEqual(len(re.findall(r"set_variable = \{ name = sr_closed_by_loss_", everything)), 1)

    def test_progress_lost_at_the_failure_stays_lost(self):
        # Owner, 2026-11-06: the milestone comes back from zero.
        for var in ("sr_progress", "sr_funding", "sr_safe", "sr_ambitious", "sr_active"):
            self.assertIn(f"remove_variable = {var}_$MILESTONE$", self.cleanup)

    def test_a_revolutions_winner_drops_the_closed_marks(self):
        self.assertIn("sr_reentry_after_civil_war = yes", _defn(EFFECTS, "sr_repair_after_civil_war"))
        after = _defn(EFFECTS, "sr_reentry_after_civil_war")
        self.assertEqual(re.findall(r"sr_reentry_forget_closure = \{ MILESTONE = (\w+)\s*\}", after),
                         list(MILESTONES))
        forget = _norm(_defn(EFFECTS, "sr_reentry_forget_closure"))
        self.assertEqual(forget, "if = { limit = { has_variable = sr_closed_by_loss_$MILESTONE$ } "
                                 "remove_variable = sr_closed_by_loss_$MILESTONE$ }")


if __name__ == "__main__":
    unittest.main()
