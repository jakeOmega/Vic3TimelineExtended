# -*- coding: utf-8 -*-
"""The Colonial Empire entry starts again after it ends.

The engine deletes a finished journal-entry record, failed or completed, and
never activates the type again: the owner's 1910 save held no je_colonial_empire
record at all for Britain, France, Spain, the Netherlands or the USA, while 211
other countries held an inactive one. So the entry's re-entry rules (a secured
empire never returns, a collapse waits ten years, a voluntary end sets no
cooldown) are made real by a monthly pass, ce_reentry_monthly
(common/scripted_effects/decolonization.txt), which adds the entry back with
add_journal_entry once a country has been due it (ce_reentry_due,
common/scripted_triggers/colonial_empire_triggers.txt) for a whole month.

Pinned here:
- ce_reentry_due restates the entry's is_shown_when_inactive and possible word
  for word (add_journal_entry skips both) and adds the decentralized,
  revolutionary, running-entry, inactive-record (the add is refused over one,
  #1416), separation-cache and voluntary-hold guards;
- the pass runs for players and AI alike, monthly, straight after the
  separation cache's step; it waits a month, adds, and clears its mark when the
  country stops being due;
- its self-check reads last month's add before it can add again, logs one line
  per add with both verdicts and ended_before=yes|unknown, reads only a marker
  naming the country itself, gives BROKEN only for a country still due the
  entry, and is in the play-test list with its fallback;
- a second ending is reachable, so every modifier an ending adds is removed
  before it is added (a same-name add_modifier stacks);
- a voluntary end holds the pass off for a year, a guard against a flickering
  colony test that possible itself does not read.
"""

import os
import re
import unittest

from je_test_helpers import old_block

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


def _enclosing(text, pos):
    """Index just after the `{` of the innermost block still open at `pos`."""
    depth = 0
    for i in range(pos - 1, -1, -1):
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                return i + 1
            depth -= 1
    return 0


JE = _read("common", "journal_entries", "je_colonial_empire.txt")
ENTRY = _block(JE, "je_colonial_empire")
TRIGGERS = _read("common", "scripted_triggers", "colonial_empire_triggers.txt")
DUE = _block(TRIGGERS, "ce_reentry_due")
EFFECTS = _read("common", "scripted_effects", "decolonization.txt")
PASS = _block(EFFECTS, "ce_reentry_monthly")
GEO_ON_ACTIONS = _read("common", "on_actions", "colonial_geography_on_actions.txt")
EVENTS = _read("events", "decolonization_events.txt")
PLAYTEST = _raw("docs", "testing", "colonial-holdings-playtest.md")

# The entry's endings: its success outcome's six events and its failure outcome's three.
END_EVENTS = ["decolonization_events.%d" % n for n in (200, 201, 202, 203, 204, 205, 206, 300, 301)]


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
                     "NOT = { has_inactive_journal_entry = je_colonial_empire }",
                     "has_variable = ce_separation_cached",
                     "NOT = { has_variable = ce_reentry_voluntary_hold }"):
            self.assertIn(cond, due)

    def test_cheap_tests_before_the_state_walk(self):
        due = _norm(DUE)
        walk = due.index("any_scope_state")
        for cond in ("has_game_rule = decolonization_enabled", "has_technology_researched = decolonization",
                     "is_country_type = decentralized", "has_journal_entry = je_colonial_empire",
                     "has_inactive_journal_entry = je_colonial_empire"):
            self.assertLess(due.index(cond), walk, cond)


class PassTests(unittest.TestCase):
    def test_monthly_after_the_cache_and_not_at_game_start(self):
        self.assertIn("colonial_geography_on_action", _block(GEO_ON_ACTIONS, "on_monthly_pulse_country"))
        monthly = _norm(_block(GEO_ON_ACTIONS, "colonial_geography_on_action"))
        self.assertIn("ce_separation_step = yes ce_reentry_monthly = yes", monthly)
        self.assertNotIn("ce_reentry_monthly", _block(GEO_ON_ACTIONS, "colonial_geography_game_start_on_action"))

    def test_for_players_and_ai_alike(self):
        # The AI must get its entry back too: no player or AI gate anywhere on
        # the way from the pulse to the add.
        hook = _block(GEO_ON_ACTIONS, "colonial_geography_on_action")
        self.assertNotIn("trigger", hook)
        for name, text in (("on_action", hook), ("pass", PASS), ("due", DUE)):
            for gate in ("is_ai", "is_player", "is_local_player"):
                self.assertNotIn(gate, text, f"{gate} in the {name}")

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

    def test_last_months_add_is_read_before_this_months(self):
        # Read after the add, the marker would be this month's own and the
        # verdict would come in the same pass as the add.
        first = re.search(r"(?<![\w.:$])if\s*=\s*\{", PASS)
        self.assertIn(self.check, PASS[first.end():_close(PASS, first.end() - 1)])
        read = PASS.index("limit = { has_variable = ce_reentry_added }")
        add = re.search(r"add_journal_entry\s*=\s*\{", PASS)
        self.assertLess(read, add.start())
        self.assertLess(read, PASS.index("set_variable = { name = ce_reentry_added"))
        self.assertNotRegex(self.check, r"add_journal_entry\s*=\s*\{")

    def test_both_verdicts_on_every_add(self):
        lines = re.findall(r'debug_log = "(TE_SELF_CHECK [^"]*)"', self.check)
        self.assertEqual(sorted(re.match(r"TE_SELF_CHECK (\w+) ce_reentry .*ended_before=(\w+)", line).groups()
                                for line in lines),
                         [("BROKEN", "unknown"), ("BROKEN", "yes"), ("OK", "unknown"), ("OK", "yes")])
        # One line per add, not once a game.
        self.assertNotIn("global_variable", PASS)
        for line in re.findall(r'debug_log = "([^"]*)"', PASS):
            self.assertNotIn("$", line)
            self.assertIn("[TimeKeeper.GetCurrentDate.GetString]", line)
            self.assertIn("[THIS.GetCountry.GetTagName]", line)
            self.assertNotIn("GetTag]", line)

    def test_ended_before_is_taken_at_the_add(self):
        # colonial_empire_has_ended is set at every ending; an entry the pass
        # added that ended within the month must not read as ended before.
        cleanup = _block(EFFECTS, "colonial_empire_je_cleanup_effect")
        self.assertIn("set_variable = colonial_empire_has_ended", cleanup)
        waited = _branch(_branch(PASS, "ce_reentry_due = yes"), "var:ce_reentry_waiting ?= scope:ce_reentry_country")
        noted = _branch(waited, "has_variable = colonial_empire_has_ended")
        self.assertIn("set_variable = ce_reentry_ended_before", noted)
        self.assertLess(waited.index("colonial_empire_has_ended"), waited.index("add_journal_entry"))
        self.assertNotIn("colonial_empire_has_ended", self.check)
        verdicts = _branch(self.check, "var:ce_reentry_added ?= scope:ce_reentry_country")
        self.assertIn("ended_before=yes", _branch(verdicts, "has_journal_entry = je_colonial_empire "
                                                            "has_variable = ce_reentry_ended_before"))

    def test_only_a_country_the_pass_added(self):
        # A revolution's winner inherits the loser's marker, which names the loser.
        verdicts = _branch(self.check, "var:ce_reentry_added ?= scope:ce_reentry_country")
        ok = _branch(verdicts, "has_journal_entry = je_colonial_empire")
        self.assertIn("TE_SELF_CHECK OK", ok)
        for broken in (_branch(verdicts, "ce_reentry_due = yes has_variable = ce_reentry_ended_before",
                               kind="else_if"),
                       _branch(verdicts, "ce_reentry_due = yes", kind="else_if")):
            self.assertIn("TE_SELF_CHECK BROKEN", broken)
            self.assertNotIn("TE_SELF_CHECK OK", broken)
        # Read once, then gone, whatever the verdict.
        after = self.check[self.check.index(verdicts) + len(verdicts):]
        self.assertIn("remove_variable = ce_reentry_added", after)
        self.assertIn("remove_variable = ce_reentry_ended_before", after)

    def test_in_the_playtest_list_with_its_fallback(self):
        rows = [line for line in PLAYTEST.splitlines() if line.startswith("| `ce_reentry` |")]
        self.assertEqual(len(rows), 1)
        self.assertIn("dormant", rows[0])
        self.assertIn("`fail`", rows[0])
        self.assertIn("ended_before=yes", rows[0])


class SecondEndingTests(unittest.TestCase):
    """A second run means a second ending, and a same-name add_modifier stacks."""

    def _blocks(self):
        yield "on_fail", old_block(ENTRY, "on_fail")
        yield "on_complete", old_block(ENTRY, "on_complete")
        for event in END_EVENTS:
            yield event, _block(EVENTS, event)
        yield "decol_grant_permanent_modifier", _block(EFFECTS, "decol_grant_permanent_modifier")

    def test_every_ending_modifier_is_removed_before_it_is_added(self):
        found = set()
        for where, text in self._blocks():
            for m in re.finditer(r"add_modifier\s*=\s*\{\s*name\s*=\s*([\w$]+)", text):
                name = m.group(1)
                found.add(name)
                with self.subTest(where=where, modifier=name):
                    before = text[_enclosing(text, m.start()):m.start()]
                    self.assertIn(f"remove_modifier_if_exists_effect = {{ MODIFIER = {name} }}", before)
        # Not vacuous: the four the collapse and the voluntary end add, and the
        # permanent rewards' helper.
        self.assertTrue({"colonial_collapse_subject_unrest_modifier", "colonial_empire_collapsed_modifier",
                         "negotiated_withdrawal_modifier", "post_imperial_modifier", "$MODIFIER$"} <= found, found)

    def test_the_endings_grant_rewards_only_through_the_helper(self):
        for where, text in self._blocks():
            if where == "decol_grant_permanent_modifier":
                continue
            with self.subTest(where=where):
                self.assertNotRegex(text, r"days\s*=\s*-1")


class VoluntaryHoldTests(unittest.TestCase):
    def setUp(self):
        self.on_fail = old_block(ENTRY, "on_fail")
        self.voluntary = _branch(self.on_fail, 'scope:journal_entry = { '
                                               '"scripted_bar_progress(colonial_stability_bar)" > 0 }')

    def test_a_voluntary_end_sets_a_years_hold(self):
        self.assertIn("decolonization_events.206", self.voluntary)
        self.assertIn("set_variable = { name = ce_reentry_voluntary_hold value = yes days = 365 }", self.voluntary)
        # Only there: a collapse has its own ten-year cooldown.
        self.assertEqual(self.on_fail.count("ce_reentry_voluntary_hold"), 1)

    def test_the_pass_waits_for_it_but_possible_does_not(self):
        self.assertIn("NOT = { has_variable = ce_reentry_voluntary_hold }", DUE)
        self.assertNotIn("ce_reentry_voluntary_hold", _block(ENTRY, "possible"))

    def test_the_readout_checklist_lists_it(self):
        checklist = _block(TRIGGERS, "ce_entry_unlocked")
        self.assertIn("NOT = { has_variable = ce_reentry_voluntary_hold }", checklist)


if __name__ == "__main__":
    unittest.main()
