"""The nuclear programme's runaway guards and the arsenal watch (2026-11-07).

France built some 1,200 warheads in an observer game, and nothing in the log said how. The weekly step finishes a
warhead for every goal its progress holds, in a `while` the engine stops only at 1,000 passes, and the AI's funding
buttons let a war and a rival believed bigger outweigh the decrease at any arsenal size. Each test pins one guard:
the loop's weekly cap, the AI's arsenal cap in the step and in the increase button, and the TE_NUCLEAR lines that
say what drove an arsenal (docs/systems/mod_systems/nuclear.md, "Runaway guards and the arsenal watch").

Run: python3 test_nuclear_runaway_guard.py
"""

import re
import unittest
from pathlib import Path

from test_nuclear_deterrence import block, read, strip_comments

ROOT = Path(__file__).resolve().parent
WEAPON_EFFECTS = ROOT / "common/scripted_effects/nuclear_weapon_effects.txt"
EXTRA_VALUES = ROOT / "common/script_values/extra_script_values.txt"
LOG_VALUES = ROOT / "common/script_values/nuclear_exchange_values.txt"
TRIGGERS = ROOT / "common/scripted_triggers/nuke_triggers.txt"
BUTTONS = ROOT / "common/scripted_buttons/nuclear_program_buttons.txt"
CUSTODY = ROOT / "common/scripted_effects/nuclear_custody_effects.txt"
JE = ROOT / "common/journal_entries/je_nuclear_program.txt"


class TestWeeklyStep(unittest.TestCase):
    def setUp(self):
        self.step = block(strip_comments(read(WEAPON_EFFECTS)), "nuclear_program_weekly_progress")

    def test_the_loop_is_capped_each_week(self):
        loop = block(self.step, "while")
        limit = block(loop, "limit")
        self.assertIn("var:nuclear_weapon_program_progress >= nuclear_weapon_program_goal_value", limit)
        self.assertIn("local_var:nd_built_this_week < nuclear_weapon_program_max_per_week", limit)
        self.assertIn("NOT = { nuclear_program_ai_at_stockpile_cap = yes }", limit)
        self.assertIn("change_local_variable = { name = nd_built_this_week add = 1 }", loop)
        self.assertLess(self.step.index("set_local_variable = { name = nd_built_this_week value = 0 }"),
                        self.step.index("while = {"))

    def test_the_weekly_cap_is_a_small_literal(self):
        values = strip_comments(read(EXTRA_VALUES))
        cap = re.search(r"^nuclear_weapon_program_max_per_week = (\d+)$", values, re.M)
        self.assertIsNotNone(cap)
        self.assertTrue(1 <= int(cap.group(1)) <= 5)

    def test_leftover_progress_is_cut_to_one_warhead(self):
        after = self.step[self.step.index("while = {"):]
        self.assertIn("limit = { var:nuclear_weapon_program_progress > nuclear_weapon_program_goal_value }", after)
        self.assertIn("value = nuclear_weapon_program_goal_value", after)
        self.assertIn("type=build_cap", after)
        self.assertIn("type=build_burst", after)

    def test_a_held_ai_is_unfunded_before_the_loop(self):
        held = self.step[:self.step.index("while = {")]
        self.assertIn("limit = { nuclear_program_ai_at_stockpile_cap = yes }", held)
        self.assertIn("name = nuclear_weapons_program_funding", held)
        self.assertIn("type=ai_stockpile_cap", held)
        self.assertIn("remove_variable = nd_ai_cap_held", held)


class TestAiCap(unittest.TestCase):
    def test_cap_is_twice_the_wish(self):
        body = block(strip_comments(read(EXTRA_VALUES)), "nuclear_ai_stockpile_cap")
        self.assertIn("value = nuclear_ai_desired_stockpile", body)
        self.assertIn("multiply = 2", body)

    def test_the_trigger_holds_only_an_ai(self):
        body = block(strip_comments(read(TRIGGERS)), "nuclear_program_ai_at_stockpile_cap")
        self.assertIn("is_ai = yes", body)
        self.assertIn("has_variable = nuclear_weapon_stockpile", body)
        self.assertIn("var:nuclear_weapon_stockpile >= nuclear_ai_stockpile_cap", body)

    def test_increase_button_is_worth_nothing_at_the_cap_last(self):
        chance = block(block(strip_comments(read(BUTTONS)), "increase_funding_nuclear_program"), "ai_chance")
        at = chance.index("limit = { nuclear_program_ai_at_stockpile_cap = yes }")
        self.assertIn("multiply = 0", chance[at:])
        # After every add and the taboo's multiply, so nothing lifts it again.
        self.assertGreater(at, chance.rindex("add ="))
        self.assertGreater(at, chance.index("multiply = nd_taboo_ai_programme_restraint_factor"))


class TestArsenalWatch(unittest.TestCase):
    def test_the_watch_runs_weekly_before_the_ledger(self):
        je = strip_comments(read(JE))
        self.assertLess(je.index("nd_log_arsenal_watch = yes"), je.index("nd_ledger_refresh = yes"))
        self.assertGreater(je.index("nd_log_arsenal_watch = yes"), je.index("nuclear_program_weekly_progress = yes"))

    def test_the_watch_logs_and_doubles(self):
        body = block(strip_comments(read(WEAPON_EFFECTS)), "nd_log_arsenal_watch")
        self.assertIn("type=arsenal_milestone", body)
        self.assertIn("change_variable = { name = nd_log_next_milestone multiply = 2 }", body)
        self.assertIn("custody_total=[THIS.ScriptValue('nd_log_custody_total_value')|0]", body)

    def test_every_log_value_exists(self):
        values = strip_comments(read(LOG_VALUES)) + strip_comments(read(EXTRA_VALUES))
        effects = strip_comments(read(WEAPON_EFFECTS)) + strip_comments(read(CUSTODY))
        names = set(re.findall(r"ScriptValue\('(nd_log_\w+|nuclear_ai_\w+)'\)", effects))
        self.assertIn("nd_log_innovation", names)
        for name in names:
            with self.subTest(value=name):
                self.assertRegex(values, rf"(?m)^{name} = ")

    def test_custody_counts_every_arrival(self):
        custody = strip_comments(read(CUSTODY))
        self.assertEqual(custody.count("change_variable = { name = nd_log_custody_total add ="), 2)
        self.assertEqual(custody.count("set_variable = { name = nd_log_custody_total value = 0 }"), 2)
        self.assertIn("warheads=[SCOPE.ScriptValue('nd_log_custody_moving')|0]", custody)


if __name__ == "__main__":
    unittest.main()
