"""Assimilation cultures: the TEMPORARY self-checks and the play-test list.

Two engine facts the system rests on that nobody has read in a game
(docs/superpowers/specs/2026-11-25-assimilation-cultures-design.md, "Unverified"):

* ``hc_define_blocks``: the define ALLOW_ASSIMILATION_REQUIRE_HERITAGE_GROUP stops the engine assimilating
  a pop into a culture of another heritage group.
* ``hc_rate_inputs``: from pop scope, the state's assimilation sum includes its country's lines, and the
  per-status assimilation switches read as the Minority Rights laws set them.

The script can't run offline, so these tests read its text: each check logs OK and BROKEN with its
numbers, once a game, behind its latch; a degenerate input gives no verdict; each has one hook; and
the play-test list carries a row for each with its fallback.

Delete this file with the checks (the header of te_assimilation_culture_selfcheck_effects.txt lists the rest).

Run: python3 -m pytest test_assimilation_cultures_selfchecks.py
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECKS = ROOT / "common/scripted_effects/te_assimilation_culture_selfcheck_effects.txt"
EFFECTS = ROOT / "common/scripted_effects/te_assimilation_culture_effects.txt"
ON_ACTIONS = ROOT / "common/on_actions/te_assimilation_culture_on_actions.txt"
PLAYTEST = ROOT / "docs/testing/assimilation-cultures-playtest.md"

# name -> (effect, latch, the guard that keeps a degenerate input from giving a verdict)
CHECKS_BY_NAME = {
    "hc_define_blocks": ("te_hc_chk_define", "te_hc_chk_define_blocks_done", r"local_var:te_hc_chk_same > 0"),
    "hc_rate_inputs": ("te_hc_chk_rate_inputs", "te_hc_chk_rate_inputs_done",
                       r"owner = \{ NOT = \{ modifier:state_assimilation_mult = 0 \} \}"),
}


def read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def code(path):
    return re.sub(r"#[^\n]*", "", read(path))


def braced(text, header):
    m = re.search(header, text, re.M)
    assert m, header
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def words(text):
    return " ".join(text.split())


def body(effect):
    return words(braced(code(CHECKS), rf"^{effect}\s*=\s*\{{"))


class VerdictTest(unittest.TestCase):
    def test_each_check_logs_ok_and_broken_with_figures(self):
        for name, (effect, _, _) in CHECKS_BY_NAME.items():
            text = body(effect)
            for verdict in ("OK", "BROKEN"):
                with self.subTest(name=name, verdict=verdict):
                    lines = re.findall(rf'debug_log = "TE_SELF_CHECK {verdict} {name} ([^"]*)"', text)
                    self.assertEqual(len(lines), 1)
                    self.assertIn("GetGlobalVariable('te_hc_chk_", lines[0])
                    self.assertIn("date=[TimeKeeper.GetCurrentDate.GetString]", lines[0])

    def test_each_check_runs_once_behind_its_latch(self):
        for name, (effect, latch, _) in CHECKS_BY_NAME.items():
            with self.subTest(name=name):
                text = body(effect)
                self.assertTrue(text.startswith(f"if = {{ limit = {{ NOT = {{ has_global_variable = {latch} }}"), text[:120])
                self.assertIn(f"set_global_variable = {{ name = {latch} value = yes }}", text)

    def test_a_degenerate_input_gives_no_verdict(self):
        for name, (effect, _, guard) in CHECKS_BY_NAME.items():
            with self.subTest(name=name):
                self.assertRegex(body(effect), guard)

    def test_the_define_check_stops_walking_the_world(self):
        # No same-group pop assimilating: three tries, then a NOT_JUDGED line and the latch.
        text = body("te_hc_chk_define")
        self.assertIn("global_var:te_hc_chk_define_armed >= 3", text)
        self.assertEqual(len(re.findall(r'debug_log = "TE_SELF_CHECK NOT_JUDGED hc_define_blocks ', text)), 1)
        self.assertEqual(text.count("set_global_variable = { name = te_hc_chk_define_blocks_done value = yes }"), 3)

    def test_the_define_check_waits_thirty_days(self):
        text = body("te_hc_chk_define")
        self.assertIn("set_global_variable = { name = te_hc_chk_define_wait value = yes days = 30 }", text)

    def test_the_printed_globals_are_removed(self):
        text = words(code(CHECKS))
        printed = set(re.findall(r"GetGlobalVariable\('(te_hc_chk_\w+)'\)", text))
        self.assertTrue(printed)
        for name in printed:
            with self.subTest(name=name):
                self.assertIn(f"remove_global_variable = {name}", text)

    def test_a_global_is_read_only_after_it_is_known_to_exist(self):
        # te_hc_chk_define_armed is the one global read in a limit that an earlier pulse set.
        text = body("te_hc_chk_define")
        read_at = text.index("global_var:te_hc_chk_define_armed >= 3")
        guard_at = text.index("has_global_variable = te_hc_chk_define_armed NOT = { has_global_variable = te_hc_chk_define_wait }")
        self.assertLess(guard_at, read_at)


class HookTest(unittest.TestCase):
    def test_the_define_check_rides_the_global_monthly_pulse(self):
        text = code(ON_ACTIONS)
        pulse = words(braced(text, r"^on_monthly_pulse\s*=\s*\{"))
        self.assertEqual(pulse, "on_actions = { te_hc_chk_define_on_action }")
        action = words(braced(text, r"^te_hc_chk_define_on_action\s*=\s*\{"))
        self.assertEqual(action, "effect = { te_hc_chk_define = yes }")

    def test_the_rate_check_is_one_call_at_the_top_of_the_conversion(self):
        text = words(code(EFFECTS))
        self.assertEqual(text.count("te_hc_chk_rate_inputs = yes"), 1)
        convert = words(braced(code(EFFECTS), r"^te_hc_convert_pop\s*=\s*\{"))
        self.assertTrue(convert.startswith("te_hc_chk_rate_inputs = yes"), convert[:80])

    def test_no_other_file_calls_a_check(self):
        for path in sorted((ROOT / "common").rglob("*.txt")) + sorted((ROOT / "events").rglob("*.txt")):
            if path in (CHECKS, EFFECTS, ON_ACTIONS):
                continue
            self.assertNotRegex(code(path), r"\bte_hc_chk_", path.name)


class PlaytestListTest(unittest.TestCase):
    def test_each_check_has_a_row_with_a_fallback(self):
        text = read(PLAYTEST)
        table = text[text.index("## Self-checks"):text.index("## What only the game shows")]
        for name in CHECKS_BY_NAME:
            with self.subTest(name=name):
                rows = [line for line in table.splitlines() if line.startswith("|") and name in line]
                self.assertEqual(len(rows), 1)
                cells = [cell.strip() for cell in rows[0].strip("|").split("|")]
                self.assertEqual(len(cells), 3)
                self.assertTrue(cells[2], "the fallback cell is empty")

    def test_the_list_names_the_files_to_delete(self):
        text = read(PLAYTEST)
        self.assertIn(CHECKS.name, text)
        self.assertIn("te_hc_chk_define_on_action", text)


if __name__ == "__main__":
    unittest.main()
