# -*- coding: utf-8 -*-
"""The Colonial Empire entry starts again after it ends.

The engine deletes a finished journal-entry record, failed or completed, and
never activates the type again: the owner's 1910 save held no je_colonial_empire
record at all for Britain, France, Spain, the Netherlands or the USA, while 211
other countries held an inactive one. So the entry's re-entry rules (a secured
empire never returns, a collapse waits ten years, a voluntary end not at all)
are made real by a monthly pass, ce_reentry_monthly
(common/scripted_effects/decolonization.txt), which adds the entry back with
add_journal_entry once a country has been due it (ce_reentry_due,
common/scripted_triggers/colonial_empire_triggers.txt) for a whole month.

Pinned here: ce_reentry_due restates the entry's is_shown_when_inactive and
possible word for word (add_journal_entry skips both) and adds the
decentralized, revolutionary, running-entry and separation-cache guards; the
pass waits a month, adds, clears its mark when the country stops being due,
and runs monthly straight after the separation cache's step; the once-a-game
self-check has both verdicts, reads only a marker naming the country itself,
gives BROKEN only for a country still due the entry, and is in the play-test
list with its fallback.
"""

import os
import re
import unittest

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


def _norm(text):
    """Whitespace-insensitive form of a script fragment."""
    return " ".join(text.split())


JE = _read("common", "journal_entries", "je_colonial_empire.txt")
ENTRY = _block(JE, "je_colonial_empire")
TRIGGERS = _read("common", "scripted_triggers", "colonial_empire_triggers.txt")
DUE = _block(TRIGGERS, "ce_reentry_due")
EFFECTS = _read("common", "scripted_effects", "decolonization.txt")
PASS = _block(EFFECTS, "ce_reentry_monthly")
GEO_ON_ACTIONS = _read("common", "on_actions", "colonial_geography_on_actions.txt")
PLAYTEST = _raw("docs", "testing", "colonial-holdings-playtest.md")


def _branch(text, opener, kind="if"):
    """The body of the first `kind` block (`if` or `else_if`) whose limit starts with `opener`."""
    for m in re.finditer(r"(?<![\w.:$])" + kind + r"\s*=\s*\{", text):
        body = text[m.end():_close(text, m.end() - 1)]
        limit = _block(body, "limit")
        if _norm(limit).startswith(_norm(opener)):
            return body
    raise AssertionError(f"no branch on {opener!r}")


class DueTests(unittest.TestCase):
    def test_restates_is_shown_when_inactive(self):
        shown = _norm(_block(ENTRY, "is_shown_when_inactive"))
        self.assertTrue(shown)
        self.assertIn(shown, _norm(DUE))

    def test_restates_possible_word_for_word(self):
        possible = _norm(_block(ENTRY, "possible"))
        for cond in ("is_overseas_colonial_state = yes", "country_has_qualifying_colonial_subject = yes",
                     "NOT = { has_variable = colonial_empire_completed }",
                     "NOT = { has_variable = colonial_empire_collapsed_recently }"):
            self.assertIn(cond, possible)
        self.assertIn(possible, _norm(DUE))

    def test_the_guards_the_add_needs(self):
        due = _norm(DUE)
        for cond in ("NOT = { is_country_type = decentralized }", "is_revolutionary = no",
                     "NOT = { has_journal_entry = je_colonial_empire }",
                     "has_variable = ce_separation_cached"):
            self.assertIn(cond, due)

    def test_cheap_tests_before_the_state_walk(self):
        due = _norm(DUE)
        walk = due.index("any_scope_state")
        for cond in ("has_game_rule = decolonization_enabled", "has_technology_researched = decolonization",
                     "is_country_type = decentralized", "has_journal_entry = je_colonial_empire"):
            self.assertLess(due.index(cond), walk, cond)


class PassTests(unittest.TestCase):
    def test_monthly_after_the_cache_and_not_at_game_start(self):
        self.assertIn("colonial_geography_on_action", _block(GEO_ON_ACTIONS, "on_monthly_pulse_country"))
        monthly = _norm(_block(GEO_ON_ACTIONS, "colonial_geography_on_action"))
        self.assertIn("ce_separation_step = yes ce_reentry_monthly = yes", monthly)
        self.assertNotIn("ce_reentry_monthly", _block(GEO_ON_ACTIONS, "colonial_geography_game_start_on_action"))

    def test_adds_only_after_a_whole_month(self):
        due = _branch(PASS, "ce_reentry_due = yes")
        # The mark names the country: a revolution's winner holds a fresh record
        # the engine activates itself, so a mark inherited from the loser must
        # not add on top of it.
        waited = _branch(due, "var:ce_reentry_waiting ?= scope:ce_reentry_country")
        self.assertIn("add_journal_entry = { type = je_colonial_empire }", _norm(waited))
        self.assertIn("remove_variable = ce_reentry_waiting", waited)
        # The first month marks, and adds nothing.
        self.assertRegex(due, r"\}\s*else = \{\s*set_variable = \{ name = ce_reentry_waiting "
                              r"value = scope:ce_reentry_country \}\s*\}")
        # The only add in the pass is the one behind the month's mark.
        self.assertEqual(len(re.findall(r"add_journal_entry\s*=\s*\{", PASS)), 1)

    def test_the_mark_goes_when_the_country_stops_being_due(self):
        cleared = _branch(PASS, "has_variable = ce_reentry_waiting", kind="else_if")
        self.assertIn("remove_variable = ce_reentry_waiting", cleared)
        self.assertNotIn("add_journal_entry", cleared)
        # That branch is the else of the due test.
        self.assertRegex(PASS, r"\}\s*else_if = \{\s*limit = \{ has_variable = ce_reentry_waiting \}")

    def test_the_add_marks_the_country_itself(self):
        self.assertIn("save_scope_as = ce_reentry_country", PASS)
        self.assertIn("set_variable = { name = ce_reentry_added value = scope:ce_reentry_country }", PASS)


class SelfCheckTests(unittest.TestCase):
    def setUp(self):
        self.check = _branch(PASS, "has_variable = ce_reentry_added")

    def test_both_verdicts_once_a_game(self):
        self.assertEqual(len(re.findall(r'"TE_SELF_CHECK OK ce_reentry ', self.check)), 1)
        self.assertEqual(len(re.findall(r'"TE_SELF_CHECK BROKEN ce_reentry ', self.check)), 1)
        self.assertEqual(self.check.count("set_global_variable = ce_reentry_selfcheck_done"), 2)
        self.assertIn("NOT = { has_global_variable = ce_reentry_selfcheck_done }", self.check)
        for line in re.findall(r'debug_log = "([^"]*)"', PASS):
            self.assertNotIn("$", line)
            self.assertIn("[TimeKeeper.GetCurrentDate.GetString]", line)
            self.assertIn("[THIS.GetCountry.GetNameNoFormatting]", line)

    def test_only_a_country_the_pass_added(self):
        # A revolution's winner inherits the loser's marker, which names the loser.
        self.assertIn("var:ce_reentry_added ?= scope:ce_reentry_country", self.check)
        verdicts = _branch(self.check, "var:ce_reentry_added ?= scope:ce_reentry_country")
        ok = _branch(verdicts, "has_journal_entry = je_colonial_empire")
        self.assertIn("TE_SELF_CHECK OK", ok)
        broken = _branch(verdicts, "ce_reentry_due = yes", kind="else_if")
        self.assertIn("TE_SELF_CHECK BROKEN", broken)
        self.assertNotIn("TE_SELF_CHECK OK", broken)
        # Read once, then gone, whatever the verdict.
        self.assertRegex(self.check, r"\}\s*remove_variable = ce_reentry_added\s*$")

    def test_in_the_playtest_list_with_its_fallback(self):
        rows = [line for line in PLAYTEST.splitlines() if line.startswith("| `ce_reentry` |")]
        self.assertEqual(len(rows), 1)
        self.assertIn("dormant", rows[0])
        self.assertIn("`fail`", rows[0])


if __name__ == "__main__":
    unittest.main()
